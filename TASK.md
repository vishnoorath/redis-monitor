## Script to monitor Farm Metadata between OLD Database Querying API and new REDIS Querying API.

- Call the OLD DB based API using POST https://prodgateway.nitara.co.in/cm/GetFarmMetaDataNew and JSON payload 
{
    "farmId": "13f9ef67-19b0-4e3d-bec5-6dd15247492c"
}


- Call the New Redis based API using POST https://prodgateway.nitara.co.in/meta-data-api/farm-meta-data and JSON payload 
{
    "farmId": "13f9ef67-19b0-4e3d-bec5-6dd15247492c"
}

- Both require an Authorization : Beaer {token} header
- Generate the token using the code below 
```python

def generate_token(farmId):

import jwt
import datetime


# Create payload
payload = {
 "userId": "c512c47d-1237-49fc-9168-bab3a2bd8b57",
  "deviceId": "7e01d642-75d1-4831-b5a6-7466e64c5c32",
  "farmId": f"{farmId}",
  "language": "EN",
  "role": "VETERINARIAN, FARMER, NITARA FIELD ADMIN, ",
  "verificationStatus": "False",
  "ModulesAccess": "NOCKIST",
  "FullName": "Mukesht live environment",
  "OrganizationId": "066b564b-7b7c-47d6-bdd8-9d7a0ce83bbe",
  "SwitchUserId": "",
  "SessionCorrelationId": "a1b3d6ed-0a24-438c-bf46-7242fe568ae8",
    "exp": datetime.datetime.now() + datetime.timedelta(minutes= 60 * 24 * 365),
    "iat": datetime.datetime.now()
}

# Encode token
#token = jwt.encode(payload, "Ds}W~GNd%0#Qb_#Mff52%$yaUfVIHujou7&*^%wrwy", algorithm="HS256")
token = jwt.encode(payload, "12345678123456781234567812345678", algorithm="HS256")

return token

```

- Compare the difference between two jsons using the DeepDiff library

```python 

!pip install deepdiff

from deepdiff import DeepDiff
import json

obj_a = {"id": 1, "meta": {"status": "active"}, "tags": [1, 2]}
obj_b = {"id": 1, "meta": {"status": "inactive"}, "tags": [1, 3]}

# Generate the difference
diff = DeepDiff(obj_a, obj_b)

print(diff)

```

### Task : TD-UI-001

Implement the following

- Settings should have a feature to store the following JSON Structure in an SQLLite DB

```json

    # Database servers to monitor (JSON object array)
    SERVERS = [
        {'server': '10.10.98.47', 'user': 'sa', 'password': 't5!bT5AZ5Q@coqZ', 'db': 'NitaraDB', 'isPrimary': True},
        {'server': '10.10.98.76', 'user': 'sa', 'password': 'Gt(#@987RTGF', 'db': 'NitaraDB', 'isPrimary': False},
    ]
```
   This must be stored as in a table ApplicationSettings with key Value pairs as columns
   The table columns will be
    key     VARCHAR, PRIMARY NOT NULL,
    value   NVARCHAR, NOT NULL
    valueType VARCHAR NO NULL 

   The value could store STRING, JSON, INT, FLOAT , BOOL , DATE etc. The type stored is indicated i the valueType column.