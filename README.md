
<p align="center">
  <img src="https://i.imgur.com/PKrSNGY.png" alt="BLACK LIVES MATTER" />

  <h3 align="center">BLACK LIVES MATTER</h3>

  <p align="center">
    <a href="https://blacklivesmatter.com/" target="_blank">Black Lives Matter</a>
    ·
    <a href="https://act.unicefusa.org/blm" target="_blank">Supporting the cause</a>
    ·
  </p>
</p>

<br />


# CHATS-ENGINE
This project provides REST and WEBSOCKETS APIs for the new customer service module @weni.ai [weni chats](https://github.com/Ilhasoft/chats-mvp)

[![Python Version](https://img.shields.io/badge/python-3.8-blue.svg)](https://www.python.org/)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-%23FE5196?logo=conventionalcommits&logoColor=white)](https://conventionalcommits.org)
[![License GPL-3.0](https://img.shields.io/badge/license-%20GPL--3.0-yellow.svg)](https://github.com/bothub-it/bothub-engine/blob/master/LICENSE)

# Requirements

* Python (3.8)
* Poetry
* Docker
* Docker-compose


# DEVELOPMENT
Define a ```.env``` file with the required enviroment variables bellow

| Command | Description |
|--|--|
| poetry install | Install dependencies and create virtual enviroment
| poetry shell | Enter virtual enviroment
| make dev_up | Run docker compose
| python manage.py makemigrations | Make migrations when changing models
| python manage.py migrate | Run migrations when changing models
| python manage.py runserver | Run the project at localhost:8000


We use swagger to document the REST api, access localhost:8000 to get the api documentation.
The Websockets api still need to be documented.


## ENVIROMENT VARIABLES
You can set environment variables in your OS or write on .env file.

| Name                           	|  Type  	| Required 	|         Default        	| Description                                                                                                                                                                          	|
|--------------------------------	|:------:	|:--------:	|:----------------------:	|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------	|
| DEBUG                          	|  Bool  	|   False  	|          False          	| If True, debug actions are made and shown in stdout.                                                                                                                                 	|
| SECRET_KEY                        |  String  	|   True  	|           None          	| Secret key used on django security.                                                                                                                                                 	|
| ALLOWED_HOSTS                     |  List  	|   False  	|            []          	| List of urls that can host this project.                                                                                                                                            	|
| DATABASE_URL                  |  String  	|   True  	|   sqlite:///db.sqlite3 	| Default database url.                                                                                                                                 	                            |
| CHANNEL_LAYERS_REDIS              |  String  	|   True  	| redis://127.0.0.1:6379/1  | Url for the redis used for django channels.                                                                                                                                         	|
| ADMIN_USER_EMAIL                  |  String  	|   False  	|       admin@weni.ai    	| Email that will receive emails with logs when something happens in the api.                                                                                                        	|
| REST_PAGINATION_SIZE              |  Int  	|   False  	|            20           	| Limit the number of objects returned when using pagination on an endpoint.                                                                                                        	|
| OLD_MESSAGES_LIMIT                |  Int  	|   False  	|            10            	| Limit the messages returned when a chat is opened.                                                                                                                                  	|
| OIDC_ENABLED | bool | False | False | Enable using OIDC.
| OIDC_RP_CLIENT_ID | string | False | None | OpenID Connect client ID provided by your OP.
| OIDC_RP_CLIENT_SECRET | string | False | None | OpenID Connect client secret provided by your OP.
| OIDC_OP_AUTHORIZATION_ENDPOINT | string | False | None | URL of your OpenID Connect provider authorization endpoint.
| OIDC_OP_TOKEN_ENDPOINT | string | False | None | URL of your OpenID Connect provider token endpoint.
| OIDC_OP_USER_ENDPOINT | string | False | None | URL of your OpenID Connect provider userinfo endpoint.
| OIDC_OP_JWKS_ENDPOINT | string | False | None | URL of your OpenID Connect provider JWKS endpoint.
| OIDC_RP_SIGN_ALGO | string | False | RS256 | Sets the algorithm the IdP uses to sign ID tokens.
| OIDC_DRF_AUTH_BACKEND | string | False | chats.apps.accounts.authentication.drf.backends.WeniOIDCAuthenticationBackend | Define the authentication middleware for the django rest framework.
| OIDC_RP_SCOPES | string | False | openid email | The OpenID Connect scopes to request during login.
| USE_S3 | Bool | False | False | Boolean that defines if S3 should be used.
| AWS_ACCESS_KEY_ID | String | False | None | Amazon S3 bucket Access Key.
| AWS_SECRET_ACCESS_KEY | String | False | None | Amazon S3 bucket Secret Key.
| AWS_STORAGE_BUCKET_NAME | String | False | None | Amazon S3 bucket name.
| USE_SENTRY | Bool | False | False | Boolean that defines if Sentry should be initialized.
| USE_SENTRY | String | False | None | Sentry's DSN URL.

# CONTRIBUTING
## Contributing

### Guidelines

If you want to contribute with bothub's projects, we made a guideline to help you. See here [contributing guidelines](https://github.com/Ilhasoft/chats-engine/blob/main/docs/CONTRIBUTING.md) for the appropriate contribution.

## License

- **[GPL 3.0](https://github.com/Ilhasoft/chats-engine/blob/main/LICENSE)**
