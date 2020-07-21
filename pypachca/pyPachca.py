import requests
import os.path
import typing


class PachcaOAuth:
	def __init__(self, client_id: str, client_secret: str, redirect_uri: str, refresh_file: str = ".refresh_token",
				code: str = None):
		self.api_url = "https://api.pachca.com/api/shared/v1"
		self.client_id = client_id
		self.client_secret = client_secret
		self.refresh_file = refresh_file
		self.redirect_uri = redirect_uri
		self.code = code

	def _save_refresh_token(self, token):
		with open(self.refresh_file, "w+") as refresh:
			refresh.write(token)

	def _get_access_from_request(self, auth_type: str):
		data = {
			"client_id": self.client_id,
			"client_secret": self.client_secret,
			"grant_type": auth_type,
			"redirect_uri": self.redirect_uri
		}
		if auth_type == "authorization_code":
			data["code"] = self.code
		elif auth_type == "refresh_token":
			data["refresh_token"] = self.refresh_token
		else:
			raise ValueError(f"auth_type должно быть 'authorization_code' или 'refresh_token'")
		response = requests.post(f"{self.api_url}/oauth/token", json=data)
		if response.status_code // 100 == 2:
			response = response.json()
			self._save_refresh_token(response["refresh_token"])
			return response["access_token"]
		elif response.status_code // 100 == 4:
			response = response.json()
			raise ValueError(f"{response['error']} - {response['error_description']}")
		else:
			raise ValueError(f"{response.text}")

	def _get_access_token(self):
		if os.path.exists(self.refresh_file):
			return self._get_access_from_request(auth_type="authorization_code")
		elif self.code:
			return self._get_access_from_request(auth_type="refresh_token")
		else:
			raise AttributeError(
				f"Отсутствует файл с refresh_token - {self.refresh_file} и код получения токена не указан")

	@property
	def access_token(self):
		return self._get_access_token()

	@property
	def refresh_token(self):
		with open(self.refresh_file, "r") as refresh:
			return refresh.read()


class Stage:
	def __init__(self, stage):
		self.id = stage["id"]
		self.name = stage["name"]
		self.sort = int(stage["sort"])


class Funnel:
	def __init__(self, funnel: dict):
		self.id = funnel["id"]
		self.name = funnel["name"]
		self.stages = [Stage(stage) for stage in funnel["stages"]]


class Property:
	def __init__(self, property_data: dict):
		self.id = property_data["id"]
		self.name = property_data["name"]
		self.data_type = property_data["data_type"]
		if "value" in property_data:
			self.value = property_data["value"]


class User:
	def __init__(self, user):
		self.id = user["id"]
		self.first_name = user["first_name"]
		self.last_name = user["last_name"]
		self.nickname = user["nickname"]
		self.email = user["email"]
		self.phone_number = user["phone_number"]
		self.department = user["department"]
		self.role = user["role"]
		self.suspended = user["suspended"]

	@property
	def full_name(self):
		return f"{self.first_name} {self.last_name}"


class Organisation:
	def __init__(self, organisation):
		self.id = organisation["id"]
		self.name = organisation["name"]
		self.inn = organisation["inn"]
		self.properties = [Property(property_data) for property_data in organisation["custom_properties"]]


class Client:
	def __init__(self, client):
		self.id = client["id"]
		self.client_number = client["client_number"]
		self.owner_id = client["owner_id"]
		self.created_at = client["created_at"]
		self.phones = client["phones"]
		self.emails = client["emails"]
		self.organization_id = client["organization_id"]
		self.additional = client["additional"]
		self.list_tags = client["list_tags"]
		self.properties = [Property(property_data) for property_data in client["custom_properties"]]


class Task:
	def __init__(self, task: dict):
		self.id: int = task["id"]
		self.kind: str = task["kind"]
		self.content: str = task["content"]
		self.due_at: str = task["due_at"]
		self.priority: int = task["priority"]
		self.user_id: int = task["user_id"]
		self.status: str = task["status"]
		self.created_at: str = task["created_at"]
		self.performer_ids: dict = task["[performer_id"]


class Deal:
	def __init__(self, deal):
		self.id = deal["id"]
		self.owner_id = deal["owner_id"]
		self.created_at = deal["created_at"]
		self.name = deal["name"]
		self.client_id = deal["client"]
		self.stage_id = deal["stage_id"]
		self.cost = deal["cost"]
		self.state = deal["state"]
		self.properties = [Property(property_data) for property_data in deal["custom_properties"]]


class Message:
	def __init__(self, message):
		self.id = message["id"]
		self.entity = message["entity"]
		self.content = message["content"]
		self.user_id = message["user_id"]
		self.created_at = message["created_at"]


class Pachca:
	def __init__(self, client_id: str, client_secret: str, redirect_uri: str, refresh_file: str = ".refresh_token",
				code: str = None):
		self.OAuth = PachcaOAuth(client_id, client_secret, redirect_uri, refresh_file, code)
		self.api_url = "https://api.pachca.com/api/shared/v1"
		self.auth = self.OAuth.access_token

	@property
	def new_auth(self):
		new = self.OAuth.access_token
		self.auth = new
		return new

	def _make_requests(self, method: str, uri: str, data: dict = None):
		if method == "GET":
			response = requests.get(f"{self.api_url}/{uri}", headers=self.auth)
			if response.status_code == 401:
				response = requests.get(f"{self.api_url}/{uri}", headers=self.new_auth)
		elif method == "POST":
			response = requests.post(f"{self.api_url}/{uri}", headers=self.auth, json=data)
			if response.status_code == 401:
				response = requests.post(f"{self.api_url}/{uri}", headers=self.new_auth, json=data)
		else:
			raise ValueError(f"method должно быть GET или POST")
		return response

	def funnels(self):
		response = self._make_requests("GET", "funnels")
		if response.status_code // 100 == 2:
			return [Funnel(funnel) for funnel in response.json()["data"]]
		elif response.status_code // 100 in [4, 5]:
			raise ValueError(f"{response.text}")

	def custom_properties(self, entity):
		if entity in ["Organization", "Client", "Deal"]:
			response = self._make_requests("GET", "custom_properties")
			if response.status_code // 100 == 2:
				return [Property(property_data) for property_data in response.json()["data"]]
			else:
				raise ValueError(f"{response.text}")
		else:
			raise ValueError(f"entity должно быть 'Organization', 'Client' или 'Deal'")

	def users(self):
		response = self._make_requests("GET", "users")
		if response.status_code // 100 == 2:
			return [User(user) for user in response.json()["data"]]
		elif response.status_code // 100 in [4, 5]:
			raise ValueError(f"{response.text}")

	def create_organisation(self, name: str = None, inn: str = None, **properties):
		if any([name, inn]):
			data = {}
			if name:
				data["name"] = name
			if inn:
				data["inn"] = inn
			if properties:
				data["custom_properties"] = []
				for prop_id, value in properties.items():
					data["custom_properties"].append({"id": int(prop_id), "value": value})
			response = self._make_requests("POST", "organizations", data={"organization": data})
			if response.status_code // 100 == 2:
				return Organisation(response.json()["data"])
			elif response.status_code // 100 in [4, 5]:
				raise ValueError(f"{response.text}")
		else:
			raise AttributeError("Не указано ни один идентификатор организации (name, inn)")

	def create_client(self,
						full_name: str,
						phones: typing.Union[int, str, list] = None,
						emails: typing.Union[int, str, list] = None,
						address: str = None,
						organization_id: int = None,
						additional: str = None,
						tags: typing.Union[str, list] = None,
						**properties):
		data = {
			"full_name": full_name}
		if phones:
			data["phones"] = phones if type(phones) is list else [phones]
		if emails:
			data["emails"] = emails if type(emails) is list else [emails]
		if address:
			data["address"] = address
		if organization_id:
			data["organization_id"] = organization_id
		if additional:
			data["additional"] = additional
		if tags:
			data["list_tags"] = tags if type(tags) is list else [tags]
		if properties:
			data["custom_properties"] = []
			for prop_id, value in properties.items():
				data["custom_properties"].append({'id': int(prop_id), 'value': value})
		response = self._make_requests("POST", "clients", data={"client": data})
		if response.status_code // 100 == 2:
			return Client(response.json()["data"])
		elif response.status_code // 100 in [4, 5]:
			raise ValueError(f"{response.text}")

	def create_task(self, kind, content: str = None, due_at: typing.Union[str, int] = None, priority: int = 1,
					performer_ids: typing.Union[int, list] = None):
		if kind in ["call", "meeting", "reminder", "event", "email"]:
			data = {
				"kind": kind,
				"priority": priority
			}
			if content:
				data["content"] = content
			if due_at:
				data["due_at"] = due_at
			if performer_ids:
				data["performer_ids"] = performer_ids if type(performer_ids) is list else [performer_ids]
			response= self._make_requests("POST", "tasks", data={"task": data})
			if response.status_code // 100 == 2:
				return response.json()["data"]
			elif response.status_code // 100 in [4, 5]:
				raise ValueError(f"{response.text}")

	def create_deal(self, name: str, client_id: int, stage_id: int, cost: int = 0,
					properties: typing.Union[list, dict] = None,
					note: typing.Union[dict, str] = None):
		data = {
			"name": name,
			"client_id": client_id,
			"stage_id": stage_id
		}
		if cost:
			data["cost"] = cost
		if properties:
			data["custom_properties"] = properties if type(properties) is list else [properties]
		if note:
			data["note"] = note if type(note) is dict else {"content": note}
		response = self._make_requests("POST", "deals", data={"deal": data})
		if response.status_code // 100 == 2:
			return response.json()["data"]
		elif response.status_code // 100 in [4, 5]:
			raise ValueError(f"{response.text}")

	def create_message(self, entity_id: int, content: str, entity_type: str = "Deal"):
		data = {
			"entity_type": entity_type,
			"entity_id": entity_id,
			"content": content
		}
		response = self._make_requests("POST", "messages", data={"message": data})
		if response.status_code // 100 == 2:
			return response.json()["data"]
		elif response.status_code // 100 in [4, 5]:
			raise ValueError(f"{response.text}")