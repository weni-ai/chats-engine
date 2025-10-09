# This is a placeholder and will be changed later to the actual flow definition

CSAT_FLOW_VERSION = 1
CSAT_FLOW_NAME = "Weni Chats CSAT Flow"
CSAT_FLOW_DEFINITION_DATA = {
    "version": "13",
    "flows": [
        {
            "name": CSAT_FLOW_NAME,
            "uuid": "23308449-eeb1-4980-8b90-b46b56a84a8a",
            "spec_version": "13.1.0",
            "language": "base",
            "type": "messaging",
            "nodes": [
                {
                    "uuid": "42b45522-07b3-4bb5-af0e-606291b1f176",
                    "actions": [
                        {
                            "attachments": [],
                            "text": "Como voc\u00ea avalia este atendimento, com uma nota de 1 a 5?\n\n1 - Muito insatisfeito\n2 - Insatisfeito\n3 - Normal\n4 - Satisfeito\n5 - Muito satisfeito",
                            "type": "send_msg",
                            "quick_replies": [],
                            "uuid": "1a906bd0-4a92-4c68-8baa-98004ee4cc4c",
                        }
                    ],
                    "exits": [
                        {
                            "uuid": "d426766c-49b7-48c6-b8bb-84114ee5f5f4",
                            "destination_uuid": "c9cfa702-c42b-4123-92ae-3ffd2a0605cb",
                        }
                    ],
                },
                {
                    "uuid": "08546d11-2b7e-4c54-a3bf-070aa60476c9",
                    "actions": [
                        {
                            "attachments": [],
                            "text": "Desculpe, n\u00e3o entendi.",
                            "type": "send_msg",
                            "quick_replies": [],
                            "uuid": "737e2707-ae3e-45f2-a1aa-fb576d01fcb6",
                        }
                    ],
                    "exits": [
                        {
                            "uuid": "386e4f04-1e8f-41da-9a5b-1d8ec1d4700d",
                            "destination_uuid": "42b45522-07b3-4bb5-af0e-606291b1f176",
                        }
                    ],
                },
                {
                    "uuid": "c9cfa702-c42b-4123-92ae-3ffd2a0605cb",
                    "actions": [],
                    "router": {
                        "type": "switch",
                        "default_category_uuid": "153b9f65-6c0a-46fd-8e58-fc1a07cfe47c",
                        "cases": [
                            {
                                "arguments": ["1", "5"],
                                "type": "has_number_between",
                                "uuid": "54cf090c-3c41-4d32-8854-c783209dc5af",
                                "category_uuid": "6e63dcdf-76b5-468d-8bc4-d469e52e5a11",
                            }
                        ],
                        "categories": [
                            {
                                "uuid": "6e63dcdf-76b5-468d-8bc4-d469e52e5a11",
                                "name": "rating",
                                "exit_uuid": "468b90ec-498d-41fc-8846-9c03899b58b3",
                            },
                            {
                                "uuid": "153b9f65-6c0a-46fd-8e58-fc1a07cfe47c",
                                "name": "Other",
                                "exit_uuid": "1262227b-8b3e-4b82-93b5-fe85cbca3cd5",
                            },
                        ],
                        "operand": "@input.text",
                        "wait": {"type": "msg"},
                        "result_name": "Rating",
                    },
                    "exits": [
                        {
                            "uuid": "468b90ec-498d-41fc-8846-9c03899b58b3",
                            "destination_uuid": "26e3eb81-a5e6-44f7-a608-d3818b315c74",
                        },
                        {
                            "uuid": "1262227b-8b3e-4b82-93b5-fe85cbca3cd5",
                            "destination_uuid": "08546d11-2b7e-4c54-a3bf-070aa60476c9",
                        },
                    ],
                },
                {
                    "uuid": "26e3eb81-a5e6-44f7-a608-d3818b315c74",
                    "actions": [
                        {
                            "uuid": "566c6c43-4355-4774-8359-9c4a57c1af96",
                            "headers": {
                                "Accept": "application/json",
                                "Authorization": "Token @trigger.params.token",
                                "Content-Type": "application/json",
                            },
                            "type": "call_webhook",
                            "url": "@trigger.params.webhook_url",
                            "body": '@(json(object(\n  "contact", object(\n    "uuid", contact.uuid, \n    "name", contact.name, \n    "urn", contact.urn\n  ),\n  "flow", object(\n    "uuid", run.flow.uuid, \n    "name", run.flow.name\n  ),\n  "room", trigger.params.room,\n  "rating", results.rating.value\n)))',
                            "method": "POST",
                            "result_name": "Result",
                        }
                    ],
                    "router": {
                        "type": "switch",
                        "operand": "@results.result.category",
                        "cases": [
                            {
                                "uuid": "fb6c727a-0050-40be-bd1e-04cf1745cd7a",
                                "type": "has_only_text",
                                "arguments": ["Success"],
                                "category_uuid": "a1fb57e6-013e-4172-b1c9-167c0b49b3c9",
                            }
                        ],
                        "categories": [
                            {
                                "uuid": "a1fb57e6-013e-4172-b1c9-167c0b49b3c9",
                                "name": "Success",
                                "exit_uuid": "afd8cfa0-45ef-467b-9ad5-859969f2c55c",
                            },
                            {
                                "uuid": "71748941-1f6e-42e6-9675-c505df6718f2",
                                "name": "Failure",
                                "exit_uuid": "cfa92737-bbcc-43ed-b9c9-10c6bfb6d678",
                            },
                        ],
                        "default_category_uuid": "71748941-1f6e-42e6-9675-c505df6718f2",
                    },
                    "exits": [
                        {
                            "uuid": "afd8cfa0-45ef-467b-9ad5-859969f2c55c",
                            "destination_uuid": None,
                        },
                        {
                            "uuid": "cfa92737-bbcc-43ed-b9c9-10c6bfb6d678",
                            "destination_uuid": None,
                        },
                    ],
                },
            ],
            "_ui": {
                "nodes": {
                    "42b45522-07b3-4bb5-af0e-606291b1f176": {
                        "position": {"left": 28, "top": 71},
                        "type": "execute_actions",
                    },
                    "08546d11-2b7e-4c54-a3bf-070aa60476c9": {
                        "position": {"left": 386, "top": 147},
                        "type": "execute_actions",
                    },
                    "c9cfa702-c42b-4123-92ae-3ffd2a0605cb": {
                        "type": "wait_for_response",
                        "position": {"left": 381, "top": 340},
                        "config": {"cases": {}},
                    },
                    "26e3eb81-a5e6-44f7-a608-d3818b315c74": {
                        "type": "split_by_webhook",
                        "position": {"left": 739, "top": 789},
                        "config": {},
                    },
                }
            },
            "revision": 59,
            "expire_after_minutes": 10080,
            "metadata": {"expires": 10080},
            "localization": {},
            "integrations": {"classifiers": [], "ticketers": []},
        }
    ],
    "campaigns": [],
    "triggers": [],
    "fields": [],
    "groups": [],
}
