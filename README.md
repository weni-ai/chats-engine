
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
| DEFAULT_DATABASE                  |  String  	|   True  	|   sqlite:///db.sqlite3 	| Default database url.                                                                                                                                 	                            |
| CHANNEL_LAYERS_REDIS              |  String  	|   True  	| redis://127.0.0.1:6379/1  | Url for the redis used for django channels.                                                                                                                                         	|
| ADMIN_USER_EMAIL                  |  String  	|   False  	|       admin@weni.ai    	| Email that will receive emails with logs when something happens in the api.                                                                                                        	|
| REST_PAGINATION_SIZE              |  Int  	|   False  	|            20           	| Limit the number of objects returned when using pagination on an endpoint.                                                                                                        	|
| OLD_MESSAGES_LIMIT                |  Int  	|   False  	|            10            	| Limit the messages returned when a chat is opened.                                                                                                                                  	|


# CONTRIBUTING
## Contributing

### Guidelines

If you want to contribute with bothub's projects, we made a guideline to help you. See here [contributing guidelines](https://github.com/Ilhasoft/chats-engine/blob/main/docs/CONTRIBUTING.md) for the appropriate contribution.

## License

- **[GPL 3.0](https://github.com/Ilhasoft/chats-engine/blob/main/LICENSE)**