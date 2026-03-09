import requests
import time
from typing import List, Optional, Dict, Any
from .logger import logger
from .models import Assignment, Actual, Project, Person

class RunnClient:
    BASE_URL = "https://api.runn.io"

    def __init__(self, token: Optional[str] = None):
        import os
        self.token = token or os.getenv("RUNN_API_TOKEN")
        if not self.token:
            from click import echo, Abort
            echo("Error: RUNN_API_TOKEN is not set. Create a .env file in the project root with:", err=True)
            echo("  RUNN_API_TOKEN=your_bearer_token_here", err=True)
            raise Abort()

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "accept": "application/json",
            "accept-version": "1.0.0"
        })

    def _request(self, method: str, path: str, params: Optional[Dict] = None, json: Optional[Dict] = None, retries: int = 3) -> Dict:
        url = f"{self.BASE_URL}{path}"
        attempt = 0
        while attempt <= retries:
            logger.debug(f"{method} {path} params={params}")
            try:
                response = self.session.request(method, url, params=params, json=json)
                logger.trace(f"Response status: {response.status_code}")
                logger.trace(f"Response body: {response.text}")

                if response.status_code == 429:
                    attempt += 1
                    if attempt > retries:
                        break
                    wait = 2 ** attempt
                    logger.debug(f"Rate limited (429). Retry {attempt}/{retries} after {wait}s.")
                    time.sleep(wait)
                    continue

                response.raise_for_status()
                return response.json() if response.text else {}
            except requests.exceptions.RequestException as e:
                logger.error(f"API Error: {e}")
                if response is not None:
                    logger.error(f"Response body: {response.text}")
                if attempt >= retries:
                    raise
                attempt += 1
                wait = 2 ** attempt
                logger.debug(f"Request failed. Retry {attempt}/{retries} after {wait}s.")
                time.sleep(wait)
        
        raise Exception(f"Failed to execute {method} {path} after {retries} retries")

    def _paginate(self, path: str, params: Optional[Dict] = None) -> List[Dict]:
        all_items = []
        current_params = params.copy() if params else {}
        current_params["limit"] = 200
        
        page = 1
        while True:
            logger.debug(f"GET {path} page {page}, cursor={current_params.get('cursor')}")
            data = self._request("GET", path, params=current_params)
            
            items = data.get("values", [])
            all_items.extend(items)
            
            next_cursor = data.get("nextCursor")
            if not next_cursor:
                break
            
            current_params["cursor"] = next_cursor
            page += 1
            
        return all_items

    def get_assignments(self, person_id: int, start_date: str, end_date: str, project_id: Optional[int] = None) -> List[Assignment]:
        params = {
            "personId": person_id,
            "startDate": start_date,
            "endDate": end_date
        }
        if project_id:
            params["projectId"] = project_id
        items = self._paginate("/assignments/", params)
        return [Assignment(
            assignmentId=i["id"],
            personId=i["personId"],
            projectId=i["projectId"],
            roleId=i["roleId"],
            minutesPerDay=i["minutesPerDay"],
            startDate=i["startDate"],
            endDate=i["endDate"],
            isBillable=i.get("isBillable", True),
            isNonWorkingDay=i.get("isNonWorkingDay", False)
        ) for i in items]

    def get_actuals(self, person_id: int, start_date: str, end_date: str, project_id: Optional[int] = None) -> List[Actual]:
        params = {
            "personId": person_id,
            "startDate": start_date,
            "endDate": end_date
        }
        if project_id:
            params["projectId"] = project_id
        items = self._paginate("/actuals/", params)
        return [Actual(
            actualId=i.get("id"),
            personId=i["personId"],
            projectId=i["projectId"],
            roleId=i["roleId"],
            date=i["date"],
            billableMinutes=i.get("billableMinutes", 0),
            nonbillableMinutes=i.get("nonbillableMinutes", 0)
        ) for i in items]

    def get_projects(self, include_archived: bool = False, name_filter: Optional[str] = None) -> Dict[int, str]:
        # Using limit=200 as specified in the original spec to minimize requests
        params = {"includeArchived": "true" if include_archived else "false"}
        if name_filter:
            params["name"] = name_filter
        items = self._paginate("/projects/", params)
        return {i["id"]: i["name"] for i in items}

    def get_people(self, email: Optional[str] = None, first_name: Optional[str] = None, last_name: Optional[str] = None) -> List[Person]:
        params = {}
        if email:
            params["email"] = email
        if first_name:
            params["firstName"] = first_name
        if last_name:
            params["lastName"] = last_name
        
        items = self._paginate("/people/", params)
        return [Person(
            personId=i["id"],
            firstName=i.get("firstName", ""),
            lastName=i.get("lastName", ""),
            email=i.get("email")
        ) for i in items]

    def post_actual(self, actual: Actual) -> Dict:
        payload = {
            "date": actual.date,
            "personId": actual.personId,
            "projectId": actual.projectId,
            "roleId": actual.roleId,
            "billableMinutes": actual.billableMinutes,
            "nonbillableMinutes": actual.nonbillableMinutes
        }
        return self._request("POST", "/actuals/", json=payload)

    def post_actuals_bulk(self, actuals: List[Actual]) -> List[Dict]:
        """
        Upsert multiple actuals in batches of up to 100.
        Ref: https://developer.runn.io/reference/post_actuals-bulk
        """
        results = []
        batch_size = 100
        
        for i in range(0, len(actuals), batch_size):
            batch = actuals[i:i + batch_size]
            payload = []
            for a in batch:
                payload.append({
                    "date": a.date,
                    "personId": a.personId,
                    "projectId": a.projectId,
                    "roleId": a.roleId,
                    "billableMinutes": a.billableMinutes,
                    "nonbillableMinutes": a.nonbillableMinutes
                })
            
            logger.info(f"Posting batch of {len(batch)} actuals to /actuals/bulk/...")
            response = self._request("POST", "/actuals/bulk/", json={"actuals": payload})
            # The API usually returns an array of results or a status object.
            # Adding it to results for tracking.
            if isinstance(response, list):
                results.extend(response)
            else:
                results.append(response)
                
        return results
