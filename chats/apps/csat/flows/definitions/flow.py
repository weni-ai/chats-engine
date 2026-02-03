# This is a placeholder and will be changed later to the actual flow definition

CSAT_FLOW_VERSION = 3
CSAT_FLOW_NAME = "Weni Chats CSAT Flow"
CSAT_FLOW_DEFINITION_DATA = {
    "version": "13",
    "site": "https://flows.weni.ai",
    "flows": [
        {
            "_ui": {
                "nodes": {
                    "69d79ef8-feb6-4ded-b9de-8607dd63d1c5": {
                        "position": {
                            "left": "1341.074049511356",
                            "top": "1219.275597947668",
                        },
                        "type": "execute_actions",
                    },
                    "90a411e4-a945-4d5c-a6c7-48e9a49bf5cd": {
                        "config": {"cases": {}},
                        "position": {
                            "left": "1344.7429126871152",
                            "top": "1474.275597947668",
                        },
                        "type": "split_by_scheme",
                    },
                    "4be8cfa8-de01-4af8-abec-7a6680de5f7f": {
                        "position": {
                            "left": "1135.002130439344",
                            "top": "1644.0453112453636",
                        },
                        "type": "execute_actions",
                    },
                    "b122e25e-084a-4902-bff9-6d3ba591c219": {
                        "position": {
                            "left": "1537.7174976978713",
                            "top": "1645.4129353706592",
                        },
                        "type": "execute_actions",
                    },
                    "3822b4b6-33ac-42e0-9ff0-add1294ba735": {
                        "position": {
                            "left": "2102.730635385634",
                            "top": "1864.5697418429131",
                        },
                        "type": "execute_actions",
                    },
                    "99ade4d9-2bf9-4e5d-99c6-6b91b9baadc2": {
                        "config": {"cases": {}},
                        "position": {
                            "left": "1157.2408609900526",
                            "top": "2031.653596440618",
                        },
                        "type": "wait_for_response",
                    },
                    "5b52d80c-5532-41ec-b1f3-6ef39fe0c8aa": {
                        "position": {
                            "left": "516.5389376101214",
                            "top": "2184.638408866735",
                        },
                        "type": "execute_actions",
                    },
                    "80924d7e-4552-4eec-92d5-d8a32536cba6": {
                        "config": {
                            "cases": {},
                            "operand": {
                                "id": "tentativa",
                                "name": "tentativa",
                                "type": "result",
                            },
                        },
                        "position": {
                            "left": "2104.7467221053703",
                            "top": "2338.4409535554537",
                        },
                        "type": "split_by_run_result",
                    },
                    "08b62de5-4c2c-416e-a0ef-3689fa01f012": {
                        "position": {"left": 521, "top": 2346},
                        "type": "execute_actions",
                    },
                    "b2884d7a-44d2-4f8b-9213-67139e322f48": {
                        "position": {
                            "left": "1243.6657730270365",
                            "top": "2384.993941290002",
                        },
                        "type": "execute_actions",
                    },
                    "8280a40f-2a0d-4f90-ba32-4d88ce6c2101": {
                        "config": {},
                        "position": {"left": "530.5389376101214", "top": 2563},
                        "type": "split_by_webhook",
                    },
                    "c0339434-f9d6-4f51-ad06-9067dc59a379": {
                        "position": {
                            "left": "1245.9127841724944",
                            "top": "2969.993941290002",
                        },
                        "type": "execute_actions",
                    },
                    "7edf7591-106c-4587-a5a7-dcbf10d58524": {
                        "position": {"left": "531.1525515926652", "top": 2784},
                        "type": "execute_actions",
                    },
                    "9c254d9b-958c-4168-9762-06d6662f8f4f": {
                        "config": {"cases": {}},
                        "position": {
                            "left": "525.4199459661597",
                            "top": "2963.3440877475277",
                        },
                        "type": "wait_for_response",
                    },
                    "103d35ae-b506-47db-8ffe-2a00c74d469e": {
                        "config": {"cases": {}},
                        "position": {
                            "left": "1262.3460900709856",
                            "top": "3166.571929565236",
                        },
                        "type": "wait_for_response",
                    },
                    "5566fb83-a3a8-4397-ba09-a6b8ff342726": {
                        "position": {
                            "left": "476.41994596615973",
                            "top": "3216.3440877475277",
                        },
                        "type": "execute_actions",
                    },
                    "ad315551-2f8d-459f-8667-a245ac11bcd6": {
                        "position": {
                            "left": "796.927464564468",
                            "top": "3224.6395402223325",
                        },
                        "type": "execute_actions",
                    },
                    "feeb9c96-e9bc-496f-a825-78dca2c02853": {
                        "position": {
                            "left": "1215.3460900709856",
                            "top": "3401.4251190743635",
                        },
                        "type": "execute_actions",
                    },
                    "168b3d89-6403-479c-b662-9f91e9c36688": {
                        "position": {
                            "left": "1479.7303603839714",
                            "top": "3403.84381983449",
                        },
                        "type": "execute_actions",
                    },
                    "611f05e2-eb39-4a86-a4ab-2ed93fc602b0": {
                        "config": {},
                        "position": {
                            "left": "908.7015043077097",
                            "top": "3790.3354566551607",
                        },
                        "type": "split_by_webhook",
                    },
                    "d283e8fe-b7dd-412f-b4a6-b7353a3af2cf": {
                        "type": "split_by_webhook",
                        "position": {
                            "left": "1248.6657730270365",
                            "top": "2682.993941290002",
                        },
                        "config": {},
                    },
                },
                "stickies": {},
            },
            "expire_after_minutes": 10080,
            "integrations": {"classifiers": [], "ticketers": []},
            "language": "base",
            "localization": {
                "eng": {
                    "05ddd58b-46a5-487a-be37-f81e27d80b41": {
                        "arguments": ["neutral normal ok"]
                    },
                    "0bae029f-1337-4a60-bc8a-9198b3e32fc8": {
                        "attachments": [],
                        "text": [
                            "Your session has ended. We will carefully review your feedback.\n\nThank you for helping us improve our service. See you next time! \ud83d\udc4b"
                        ],
                    },
                    "0d7a4e3a-8c8b-429e-928d-29fb1cbf890c": {
                        "arguments": ["Dissatisfied \ud83d\ude41"]
                    },
                    "173c606e-982b-4089-971a-431693ef3d70": {
                        "attachments": [],
                        "text": [
                            "Leave a comment about your experience with our service \u270d\ufe0f"
                        ],
                    },
                    "1ec39b32-3f65-46a8-9620-11bb3e05e194": {"arguments": ["bad poor"]},
                    "33235346-c876-4ee3-a39e-5ed123ac4b67": {
                        "description": [""],
                        "title": ["Very satisfied \ud83d\ude03"],
                    },
                    "34c7fba2-b6ee-49d5-8670-75fe0fc61477": {
                        "button_text": ["Select here"],
                        "footer": [
                            "It\u2019s very quick, it won\u2019t even take a minute."
                        ],
                        "header_text": ["Customer Satisfaction Survey"],
                        "quick_replies": [],
                        "text": ["*How would you rate my service?* \ud83d\udc47"],
                    },
                    "3623496b-56da-4d53-83da-d9e5c77dd022": {
                        "description": [""],
                        "title": ["Neutral \ud83d\ude36"],
                    },
                    "37c084c0-4363-4ca6-8516-efbd64e1615b": {
                        "description": [""],
                        "title": ["Satisfied \ud83d\ude42"],
                    },
                    "49579fb1-c2ef-4b2b-acf0-592945ccf56a": {
                        "arguments": ["Very satisfied \ud83d\ude03"]
                    },
                    "4cd3777a-369d-408b-8625-8335c1cf01fa": {
                        "attachments": [],
                        "text": [
                            "Your session has ended.\n\nThank you for your feedback. See you next time! \ud83d\udc4b"
                        ],
                    },
                    "669f1b88-4aca-4a41-947d-17cbc5f6b262": {
                        "arguments": ["Satisfied \ud83d\ude42"]
                    },
                    "99303991-ca7d-4fcb-81b3-616186f8117d": {
                        "arguments": ["terrible horrible"]
                    },
                    "9a442124-6e7a-4a5c-855b-f6df6b5da640": {
                        "description": [""],
                        "title": ["Very dissatisfied \ud83d\ude23"],
                    },
                    "abca96a7-9704-4a0b-b72f-cd7aa23178ed": {
                        "arguments": ["Very dissatisfied \ud83d\ude23"]
                    },
                    "affbf9c6-742e-4d7b-a9e3-d46b8d420678": {
                        "arguments": ["Neutral \ud83d\ude36"]
                    },
                    "b2ccd0c6-17dd-4a16-9420-9fbd8bdf63f4": {
                        "arguments": ["satisfied"]
                    },
                    "cb89ec39-e25c-4f9a-a6ea-7e694c66c251": {
                        "text": ["**How would you rate my service?** \ud83d\udc47"],
                        "attachments": [],
                        "quick_replies": [
                            "Very dissatisfied \ud83d\ude23",
                            "Dissatisfied \ud83d\ude41",
                            "Neutral \ud83d\ude36",
                            "Satisfied \ud83d\ude42",
                            "Very satisfied \ud83d\ude03",
                        ],
                    },
                    "ce4dc887-831a-46a4-92df-56f4e7935c71": {"arguments": ["good"]},
                    "cff06c3e-435c-488f-a594-ae102633c14d": {
                        "attachments": [],
                        "text": [
                            "Leave a comment so we can keep improving our service \u270d\ufe0f"
                        ],
                    },
                    "dd108f48-e89d-42c9-b0d7-630eab57a170": {
                        "attachments": [],
                        "text": [
                            "Before continuing, could you please answer our survey below?"
                        ],
                    },
                    "df6b0d82-e1f7-42f0-aace-7db87ddb9d69": {
                        "description": [""],
                        "title": ["Dissatisfied \ud83d\ude41"],
                    },
                    "efcca434-16d5-4225-8b1d-1f89cd6e4e1b": {"arguments": ["great"]},
                },
                "por": {
                    "0bae029f-1337-4a60-bc8a-9198b3e32fc8": {
                        "attachments": [],
                        "text": [
                            "Seu atendimento foi finalizado. Iremos analisar seu coment\u00e1rio com responsabilidade.\n\nAgradecemos a sua colabora\u00e7\u00e3o para melhorar o atendimento. At\u00e9 a pr\u00f3xima \ud83d\udc4b"
                        ],
                    },
                    "173c606e-982b-4089-971a-431693ef3d70": {
                        "attachments": [],
                        "text": [
                            "Deixe um coment\u00e1rio sobre sua experi\u00eancia com nosso atendimento \u270d\ufe0f"
                        ],
                    },
                    "33235346-c876-4ee3-a39e-5ed123ac4b67": {
                        "description": [""],
                        "title": ["Muito satisfeito \ud83d\ude03"],
                    },
                    "34c7fba2-b6ee-49d5-8670-75fe0fc61477": {
                        "button_text": ["Selecione aqui"],
                        "footer": [
                            "\u00c9 bem r\u00e1pido, n\u00e3o vai demorar nem 1 minuto."
                        ],
                        "header_text": ["Pesquisa de Satisfa\u00e7\u00e3o"],
                        "quick_replies": [],
                        "text": [
                            "*Como voc\u00ea avalia o meu atendimento?* \ud83d\udc47"
                        ],
                    },
                    "3623496b-56da-4d53-83da-d9e5c77dd022": {
                        "description": [""],
                        "title": ["Neutro \ud83d\ude36"],
                    },
                    "37c084c0-4363-4ca6-8516-efbd64e1615b": {
                        "description": [""],
                        "title": ["Satisfeito \ud83d\ude42"],
                    },
                    "4cd3777a-369d-408b-8625-8335c1cf01fa": {
                        "attachments": [],
                        "text": [
                            "Seu atendimento foi finalizado.\n\nAgradecemos a sua colabora\u00e7\u00e3o. At\u00e9 a pr\u00f3xima \ud83d\udc4b"
                        ],
                    },
                    "9a442124-6e7a-4a5c-855b-f6df6b5da640": {
                        "description": [""],
                        "title": ["Muito insatisfeito \ud83d\ude23"],
                    },
                    "cb89ec39-e25c-4f9a-a6ea-7e694c66c251": {
                        "text": [
                            "**Como voc\u00ea avalia o meu atendimento?** \ud83d\udc47"
                        ],
                        "attachments": [],
                    },
                    "cff06c3e-435c-488f-a594-ae102633c14d": {
                        "attachments": [],
                        "text": [
                            "Deixe um coment\u00e1rio para sempre melhorarmos nosso atendimento \u270d\ufe0f"
                        ],
                    },
                    "dd108f48-e89d-42c9-b0d7-630eab57a170": {
                        "attachments": [],
                        "text": [
                            "Antes de continuar, poderia responder nossa pesquisa abaixo?"
                        ],
                    },
                    "df6b0d82-e1f7-42f0-aace-7db87ddb9d69": {
                        "description": [""],
                        "title": ["Insatisfeito \ud83d\ude41"],
                    },
                },
                "spa": {
                    "05ddd58b-46a5-487a-be37-f81e27d80b41": {
                        "arguments": ["normal neutral"]
                    },
                    "0bae029f-1337-4a60-bc8a-9198b3e32fc8": {
                        "attachments": [],
                        "text": [
                            "Tu atenci\u00f3n ha finalizado. Analizaremos tu comentario con responsabilidad.\n\nGracias por ayudarnos a mejorar nuestra atenci\u00f3n. \u00a1Hasta la pr\u00f3xima! \ud83d\udc4b"
                        ],
                    },
                    "0d7a4e3a-8c8b-429e-928d-29fb1cbf890c": {
                        "arguments": ["Insatisfecho \ud83d\ude41"]
                    },
                    "173c606e-982b-4089-971a-431693ef3d70": {
                        "attachments": [],
                        "text": [
                            "D\u00e9janos un comentario sobre tu experiencia con nuestra atenci\u00f3n \u270d\ufe0f"
                        ],
                    },
                    "1ec39b32-3f65-46a8-9620-11bb3e05e194": {
                        "arguments": ["malo mala"]
                    },
                    "33235346-c876-4ee3-a39e-5ed123ac4b67": {
                        "description": [""],
                        "title": ["Muy satisfecho \ud83d\ude03"],
                    },
                    "34c7fba2-b6ee-49d5-8670-75fe0fc61477": {
                        "button_text": ["Selecciona aqu\u00ed"],
                        "footer": [
                            "Es muy r\u00e1pido, no te quitar\u00e1 ni un minuto."
                        ],
                        "header_text": ["Encuesta de Satisfacci\u00f3n"],
                        "quick_replies": [],
                        "text": [
                            "*\u00bfC\u00f3mo valoras mi atenci\u00f3n?* \ud83d\udc47"
                        ],
                    },
                    "3623496b-56da-4d53-83da-d9e5c77dd022": {
                        "description": [""],
                        "title": ["Neutral \ud83d\ude36"],
                    },
                    "37c084c0-4363-4ca6-8516-efbd64e1615b": {
                        "description": [""],
                        "title": ["Satisfecho \ud83d\ude42"],
                    },
                    "49579fb1-c2ef-4b2b-acf0-592945ccf56a": {
                        "arguments": ["Muy satisfecho \ud83d\ude03"]
                    },
                    "4cd3777a-369d-408b-8625-8335c1cf01fa": {
                        "attachments": [],
                        "text": [
                            "Tu atenci\u00f3n ha finalizado.\n\nAgradecemos tu colaboraci\u00f3n. \u00a1Hasta la pr\u00f3xima! \ud83d\udc4b"
                        ],
                    },
                    "669f1b88-4aca-4a41-947d-17cbc5f6b262": {
                        "arguments": ["Satisfecho \ud83d\ude42"]
                    },
                    "99303991-ca7d-4fcb-81b3-616186f8117d": {
                        "arguments": ["horrible terrible"]
                    },
                    "9a442124-6e7a-4a5c-855b-f6df6b5da640": {
                        "description": [""],
                        "title": ["Muy insatisfecho \ud83d\ude23"],
                    },
                    "abca96a7-9704-4a0b-b72f-cd7aa23178ed": {
                        "arguments": ["Muy insatisfecho \ud83d\ude23"]
                    },
                    "affbf9c6-742e-4d7b-a9e3-d46b8d420678": {
                        "arguments": ["Neutral \ud83d\ude36"]
                    },
                    "b2ccd0c6-17dd-4a16-9420-9fbd8bdf63f4": {
                        "arguments": ["satisfecho satisfecha"]
                    },
                    "cb89ec39-e25c-4f9a-a6ea-7e694c66c251": {
                        "text": [
                            "**\u00bfC\u00f3mo valoras mi atenci\u00f3n?** \ud83d\udc47"
                        ],
                        "attachments": [],
                        "quick_replies": [
                            "Muy insatisfecho \ud83d\ude23",
                            "Insatisfecho \ud83d\ude41",
                            "Neutral \ud83d\ude36",
                            "Satisfecho \ud83d\ude42",
                            "Muy satisfecho \ud83d\ude03",
                        ],
                    },
                    "ce4dc887-831a-46a4-92df-56f4e7935c71": {
                        "arguments": ["bueno buena"]
                    },
                    "cff06c3e-435c-488f-a594-ae102633c14d": {
                        "attachments": [],
                        "text": [
                            "D\u00e9janos un comentario para que podamos seguir mejorando nuestra atenci\u00f3n \u270d\ufe0f"
                        ],
                    },
                    "dd108f48-e89d-42c9-b0d7-630eab57a170": {
                        "attachments": [],
                        "text": [
                            "Antes de continuar, \u00bfpodr\u00edas responder a nuestra encuesta de abajo?"
                        ],
                    },
                    "df6b0d82-e1f7-42f0-aace-7db87ddb9d69": {
                        "description": [""],
                        "title": ["Insatisfecho \ud83d\ude41"],
                    },
                    "efcca434-16d5-4225-8b1d-1f89cd6e4e1b": {
                        "arguments": ["excelente"]
                    },
                },
            },
            "metadata": {"expires": 10080},
            "name": "Weni Chats CSAT Flow",
            "nodes": [
                {
                    "actions": [
                        {
                            "category": "",
                            "name": "tentativa",
                            "type": "set_run_result",
                            "uuid": "ae5ce134-21b0-4142-acf8-8751354518ca",
                            "value": "0",
                        },
                        {
                            "attachments": [],
                            "quick_replies": [],
                            "text": "Antes de encerrar, conte como foi sua experi\u00eancia!",
                            "type": "send_msg",
                            "uuid": "761ef049-6cf5-4cd6-86cf-4f8bad44a1e5",
                        },
                    ],
                    "exits": [
                        {
                            "destination_uuid": "90a411e4-a945-4d5c-a6c7-48e9a49bf5cd",
                            "uuid": "d747e48e-3003-4b93-be93-f37e7e185d22",
                        }
                    ],
                    "uuid": "69d79ef8-feb6-4ded-b9de-8607dd63d1c5",
                },
                {
                    "actions": [],
                    "exits": [
                        {
                            "destination_uuid": "4be8cfa8-de01-4af8-abec-7a6680de5f7f",
                            "uuid": "48488953-2fec-47eb-8358-4511432936aa",
                        },
                        {
                            "destination_uuid": "b122e25e-084a-4902-bff9-6d3ba591c219",
                            "uuid": "c07647d1-704d-4cbc-81d8-e11b0c60651f",
                        },
                    ],
                    "router": {
                        "cases": [
                            {
                                "arguments": ["whatsapp"],
                                "category_uuid": "c690b59b-e729-42cd-861e-dc1995cfca60",
                                "type": "has_only_phrase",
                                "uuid": "a196a992-67c5-4183-a062-93855796c442",
                            }
                        ],
                        "categories": [
                            {
                                "exit_uuid": "48488953-2fec-47eb-8358-4511432936aa",
                                "name": "WhatsApp",
                                "uuid": "c690b59b-e729-42cd-861e-dc1995cfca60",
                            },
                            {
                                "exit_uuid": "c07647d1-704d-4cbc-81d8-e11b0c60651f",
                                "name": "Other",
                                "uuid": "0ff7d78b-8f07-4671-9314-44f1007f4e12",
                            },
                        ],
                        "default_category_uuid": "0ff7d78b-8f07-4671-9314-44f1007f4e12",
                        "operand": "@(urn_parts(contact.urn).scheme)",
                        "result_name": "",
                        "type": "switch",
                    },
                    "uuid": "90a411e4-a945-4d5c-a6c7-48e9a49bf5cd",
                },
                {
                    "actions": [
                        {
                            "type": "send_whatsapp_msg",
                            "text": "*Como voc\u00ea avalia o meu atendimento?* \ud83d\udc47",
                            "messageType": "interactive",
                            "header_type": "text",
                            "header_text": "Pesquisa de Satisfa\u00e7\u00e3o",
                            "footer": "\u00c9 bem r\u00e1pido, n\u00e3o vai demorar nem 1 minuto.",
                            "interaction_type": "list",
                            "button_text": "Selecione aqui",
                            "list_items": [
                                {
                                    "description": "",
                                    "title": "Muito insatisfeito \ud83d\ude23",
                                    "uuid": "9a442124-6e7a-4a5c-855b-f6df6b5da640",
                                },
                                {
                                    "description": "",
                                    "title": "Insatisfeito \ud83d\ude41",
                                    "uuid": "df6b0d82-e1f7-42f0-aace-7db87ddb9d69",
                                },
                                {
                                    "description": "",
                                    "title": "Neutro \ud83d\ude36",
                                    "uuid": "3623496b-56da-4d53-83da-d9e5c77dd022",
                                },
                                {
                                    "description": "",
                                    "title": "Satisfeito \ud83d\ude42",
                                    "uuid": "37c084c0-4363-4ca6-8516-efbd64e1615b",
                                },
                                {
                                    "description": "",
                                    "title": "Muito satisfeito \ud83d\ude03",
                                    "uuid": "33235346-c876-4ee3-a39e-5ed123ac4b67",
                                },
                            ],
                            "uuid": "34c7fba2-b6ee-49d5-8670-75fe0fc61477",
                            "flow_data_attachment_name_map": {},
                            "quick_replies": [],
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "99ade4d9-2bf9-4e5d-99c6-6b91b9baadc2",
                            "uuid": "fadddc2f-9bd2-4d0b-8b10-492c32205e1c",
                        }
                    ],
                    "uuid": "4be8cfa8-de01-4af8-abec-7a6680de5f7f",
                },
                {
                    "actions": [
                        {
                            "attachments": [],
                            "text": "**Como voc\u00ea avalia o meu atendimento?** \ud83d\udc47",
                            "type": "send_msg",
                            "quick_replies": [
                                "Muito insatisfeito \ud83d\ude23",
                                "Insatisfeito \ud83d\ude41",
                                "Neutro \ud83d\ude36",
                                "Satisfeito \ud83d\ude42",
                                "Muito satisfeito \ud83d\ude03",
                            ],
                            "uuid": "cb89ec39-e25c-4f9a-a6ea-7e694c66c251",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "99ade4d9-2bf9-4e5d-99c6-6b91b9baadc2",
                            "uuid": "6e0656f5-a7a3-4f70-84d6-3084244bf0ad",
                        }
                    ],
                    "uuid": "b122e25e-084a-4902-bff9-6d3ba591c219",
                },
                {
                    "actions": [
                        {
                            "attachments": [],
                            "quick_replies": [],
                            "text": "Sua opini\u00e3o \u00e9 muito importante para n\u00f3s e leva menos de 1 minuto. Agradecemos se puder responder.",
                            "type": "send_msg",
                            "uuid": "dd108f48-e89d-42c9-b0d7-630eab57a170",
                        },
                        {
                            "category": "",
                            "name": "tentativa",
                            "type": "set_run_result",
                            "uuid": "b36e99b6-e3c2-4ac7-9fc2-768caff19ec4",
                            "value": "@(results.tentativa +1)",
                        },
                    ],
                    "exits": [
                        {
                            "destination_uuid": "90a411e4-a945-4d5c-a6c7-48e9a49bf5cd",
                            "uuid": "9ac18eb0-950c-4535-8334-7bf0812e8f9f",
                        }
                    ],
                    "uuid": "3822b4b6-33ac-42e0-9ff0-add1294ba735",
                },
                {
                    "actions": [],
                    "exits": [
                        {
                            "destination_uuid": "5b52d80c-5532-41ec-b1f3-6ef39fe0c8aa",
                            "uuid": "4d8ff698-2e6e-4abe-9a41-ff0d85b10b16",
                        },
                        {
                            "destination_uuid": "5b52d80c-5532-41ec-b1f3-6ef39fe0c8aa",
                            "uuid": "b9754822-0e43-4d61-bda1-b9e883947bae",
                        },
                        {
                            "destination_uuid": "b2884d7a-44d2-4f8b-9213-67139e322f48",
                            "uuid": "126a8703-c83c-4607-8cd0-c43708b54b71",
                        },
                        {
                            "destination_uuid": "b2884d7a-44d2-4f8b-9213-67139e322f48",
                            "uuid": "4ad947ed-04f7-49cb-a21d-73e11c36928b",
                        },
                        {
                            "destination_uuid": "b2884d7a-44d2-4f8b-9213-67139e322f48",
                            "uuid": "72d82222-1d47-4421-86a2-f9be36bcfcd8",
                        },
                        {
                            "destination_uuid": "80924d7e-4552-4eec-92d5-d8a32536cba6",
                            "uuid": "031a93b3-71cc-4f6e-8c90-228ae5ca1ec2",
                        },
                        {
                            "destination_uuid": "80924d7e-4552-4eec-92d5-d8a32536cba6",
                            "uuid": "3b1f3c5e-1b0a-4fa0-98c0-cb595ba1467f",
                        },
                    ],
                    "router": {
                        "cases": [
                            {
                                "arguments": ["Muito satisfeito \ud83d\ude03"],
                                "category_uuid": "c5fe2543-48ff-4c1a-9951-50ab5cf3cd49",
                                "type": "has_only_phrase",
                                "uuid": "49579fb1-c2ef-4b2b-acf0-592945ccf56a",
                            },
                            {
                                "arguments": ["Satisfeito \ud83d\ude42"],
                                "category_uuid": "760e73d8-9bd6-4cd0-9068-12114fa76371",
                                "type": "has_only_phrase",
                                "uuid": "669f1b88-4aca-4a41-947d-17cbc5f6b262",
                            },
                            {
                                "arguments": ["Neutro \ud83d\ude36"],
                                "category_uuid": "c90f92c4-a031-47fb-8f69-010bded0beda",
                                "type": "has_only_phrase",
                                "uuid": "affbf9c6-742e-4d7b-a9e3-d46b8d420678",
                            },
                            {
                                "arguments": ["Insatisfeito \ud83d\ude41"],
                                "category_uuid": "35bf88d5-d8db-437d-a02c-ef77e1fe3e7e",
                                "type": "has_only_phrase",
                                "uuid": "0d7a4e3a-8c8b-429e-928d-29fb1cbf890c",
                            },
                            {
                                "arguments": ["Muito insatisfeito \ud83d\ude23"],
                                "category_uuid": "e566267a-8a4d-462a-92e6-cc43e81712da",
                                "type": "has_only_phrase",
                                "uuid": "abca96a7-9704-4a0b-b72f-cd7aa23178ed",
                            },
                            {
                                "arguments": ["\u00f3timo otimo"],
                                "category_uuid": "c5fe2543-48ff-4c1a-9951-50ab5cf3cd49",
                                "type": "has_any_word",
                                "uuid": "efcca434-16d5-4225-8b1d-1f89cd6e4e1b",
                            },
                            {
                                "arguments": ["bom boa"],
                                "category_uuid": "760e73d8-9bd6-4cd0-9068-12114fa76371",
                                "type": "has_any_word",
                                "uuid": "ce4dc887-831a-46a4-92df-56f4e7935c71",
                            },
                            {
                                "arguments": ["neutro neutra normal"],
                                "category_uuid": "c90f92c4-a031-47fb-8f69-010bded0beda",
                                "type": "has_any_word",
                                "uuid": "05ddd58b-46a5-487a-be37-f81e27d80b41",
                            },
                            {
                                "arguments": ["ruim rum"],
                                "category_uuid": "35bf88d5-d8db-437d-a02c-ef77e1fe3e7e",
                                "type": "has_any_word",
                                "uuid": "1ec39b32-3f65-46a8-9620-11bb3e05e194",
                            },
                            {
                                "arguments": ["p\u00e9ssimo pessimo pesimo"],
                                "category_uuid": "e566267a-8a4d-462a-92e6-cc43e81712da",
                                "type": "has_any_word",
                                "uuid": "99303991-ca7d-4fcb-81b3-616186f8117d",
                            },
                            {
                                "arguments": ["satisfeito satisfeita"],
                                "category_uuid": "760e73d8-9bd6-4cd0-9068-12114fa76371",
                                "type": "has_any_word",
                                "uuid": "b2ccd0c6-17dd-4a16-9420-9fbd8bdf63f4",
                            },
                        ],
                        "categories": [
                            {
                                "exit_uuid": "4d8ff698-2e6e-4abe-9a41-ff0d85b10b16",
                                "name": "5",
                                "uuid": "c5fe2543-48ff-4c1a-9951-50ab5cf3cd49",
                            },
                            {
                                "exit_uuid": "b9754822-0e43-4d61-bda1-b9e883947bae",
                                "name": "4",
                                "uuid": "760e73d8-9bd6-4cd0-9068-12114fa76371",
                            },
                            {
                                "exit_uuid": "126a8703-c83c-4607-8cd0-c43708b54b71",
                                "name": "3",
                                "uuid": "c90f92c4-a031-47fb-8f69-010bded0beda",
                            },
                            {
                                "exit_uuid": "4ad947ed-04f7-49cb-a21d-73e11c36928b",
                                "name": "2",
                                "uuid": "35bf88d5-d8db-437d-a02c-ef77e1fe3e7e",
                            },
                            {
                                "exit_uuid": "72d82222-1d47-4421-86a2-f9be36bcfcd8",
                                "name": "1",
                                "uuid": "e566267a-8a4d-462a-92e6-cc43e81712da",
                            },
                            {
                                "exit_uuid": "031a93b3-71cc-4f6e-8c90-228ae5ca1ec2",
                                "name": "Other",
                                "uuid": "4f0b991f-3555-443d-a8a8-304c97aaa6e7",
                            },
                            {
                                "exit_uuid": "3b1f3c5e-1b0a-4fa0-98c0-cb595ba1467f",
                                "name": "No Response",
                                "uuid": "b5aa610c-0add-40ce-8a17-4b6451c56445",
                            },
                        ],
                        "default_category_uuid": "4f0b991f-3555-443d-a8a8-304c97aaa6e7",
                        "operand": "@input.text",
                        "result_name": "avaliacao",
                        "type": "switch",
                        "wait": {
                            "timeout": {
                                "category_uuid": "b5aa610c-0add-40ce-8a17-4b6451c56445",
                                "seconds": 600,
                            },
                            "type": "msg",
                        },
                    },
                    "uuid": "99ade4d9-2bf9-4e5d-99c6-6b91b9baadc2",
                },
                {
                    "actions": [
                        {
                            "field": {
                                "key": "nota_pesquisa_atendimento_humano",
                                "name": "Nota Pesquisa Atendimento Humano",
                            },
                            "type": "set_contact_field",
                            "uuid": "a69e78f1-5bba-47aa-91ff-04fd1ec3858c",
                            "value": "@results.avaliacao.category",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "08b62de5-4c2c-416e-a0ef-3689fa01f012",
                            "uuid": "ee555105-5415-42ef-b2b4-555c62aeb358",
                        }
                    ],
                    "uuid": "5b52d80c-5532-41ec-b1f3-6ef39fe0c8aa",
                },
                {
                    "actions": [],
                    "exits": [
                        {
                            "destination_uuid": None,
                            "uuid": "22048f71-46bc-46e3-91de-0e2be2a0194f",
                        },
                        {
                            "destination_uuid": "3822b4b6-33ac-42e0-9ff0-add1294ba735",
                            "uuid": "4a53d7da-d83d-40d3-8816-a13145b28065",
                        },
                    ],
                    "router": {
                        "cases": [
                            {
                                "arguments": ["1"],
                                "category_uuid": "0a1c27d6-3da0-4598-8326-d12e3b513b70",
                                "type": "has_any_word",
                                "uuid": "e90fb06b-72d8-442f-b06a-fd366cd65ffc",
                            }
                        ],
                        "categories": [
                            {
                                "exit_uuid": "22048f71-46bc-46e3-91de-0e2be2a0194f",
                                "name": "J\u00e1 tentou 1x",
                                "uuid": "0a1c27d6-3da0-4598-8326-d12e3b513b70",
                            },
                            {
                                "exit_uuid": "4a53d7da-d83d-40d3-8816-a13145b28065",
                                "name": "Other",
                                "uuid": "b2130bb8-2543-47b1-8231-fd12f0f89f5b",
                            },
                        ],
                        "default_category_uuid": "b2130bb8-2543-47b1-8231-fd12f0f89f5b",
                        "operand": "@results.tentativa",
                        "type": "switch",
                    },
                    "uuid": "80924d7e-4552-4eec-92d5-d8a32536cba6",
                },
                {
                    "actions": [
                        {
                            "category": "@results.avaliacao.category",
                            "name": "avaliacao",
                            "type": "set_run_result",
                            "uuid": "3a93d8a9-732b-4340-8cc3-98fc07ea9f7a",
                            "value": "@results.avaliacao.category",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "8280a40f-2a0d-4f90-ba32-4d88ce6c2101",
                            "uuid": "da4a6658-b637-42a8-ba76-713d4a34a48c",
                        }
                    ],
                    "uuid": "08b62de5-4c2c-416e-a0ef-3689fa01f012",
                },
                {
                    "actions": [
                        {
                            "uuid": "be00b5a3-4e35-4a52-afa7-e22800ab77a2",
                            "type": "set_contact_field",
                            "field": {
                                "name": "Nota Pesquisa Atendimento Humano",
                                "key": "nota_pesquisa_atendimento_humano",
                            },
                            "value": "@results.avaliacao.category",
                        },
                        {
                            "type": "set_run_result",
                            "name": "avaliacao",
                            "value": "@results.avaliacao.category",
                            "category": "@results.avaliacao.category",
                            "uuid": "98af8de6-d712-4c14-b072-548f5fabad71",
                        },
                    ],
                    "exits": [
                        {
                            "destination_uuid": "d283e8fe-b7dd-412f-b4a6-b7353a3af2cf",
                            "uuid": "d617bb4d-aefc-4567-b03f-690df4dfa81f",
                        }
                    ],
                    "uuid": "b2884d7a-44d2-4f8b-9213-67139e322f48",
                },
                {
                    "actions": [
                        {
                            "body": '@(json(object(\n  "contact", object(\n    "uuid", contact.uuid, \n    "name", contact.name, \n    "urn", contact.urn\n  ),\n  "flow", object(\n    "uuid", run.flow.uuid, \n    "name", run.flow.name\n  ),\n  "room", trigger.params.room,\n  "rating", results.avaliacao.value\n)))',
                            "headers": {
                                "Accept": "application/json",
                                "Authorization": "Token @trigger.params.token",
                                "Content-Type": "application/json",
                            },
                            "method": "POST",
                            "result_name": "Result",
                            "type": "call_webhook",
                            "url": "@trigger.params.webhook_url",
                            "uuid": "bff07afd-67a4-424e-8913-5f2042b4b101",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "7edf7591-106c-4587-a5a7-dcbf10d58524",
                            "uuid": "ff733448-e1ee-4e03-bafd-ea8d85b55d22",
                        },
                        {
                            "destination_uuid": "7edf7591-106c-4587-a5a7-dcbf10d58524",
                            "uuid": "e99bf438-2bf4-4ab7-beef-9145c5db5330",
                        },
                    ],
                    "router": {
                        "cases": [
                            {
                                "arguments": ["Success"],
                                "category_uuid": "7dcde587-dbda-4304-8db0-58bcaf7ddffc",
                                "type": "has_only_text",
                                "uuid": "f981ba89-f393-4383-9453-35fa0bdb5a1e",
                            }
                        ],
                        "categories": [
                            {
                                "exit_uuid": "ff733448-e1ee-4e03-bafd-ea8d85b55d22",
                                "name": "Success",
                                "uuid": "7dcde587-dbda-4304-8db0-58bcaf7ddffc",
                            },
                            {
                                "exit_uuid": "e99bf438-2bf4-4ab7-beef-9145c5db5330",
                                "name": "Failure",
                                "uuid": "9e7f4ca0-b965-41a3-a300-43b673e6e740",
                            },
                        ],
                        "default_category_uuid": "9e7f4ca0-b965-41a3-a300-43b673e6e740",
                        "operand": "@results.result.category",
                        "type": "switch",
                    },
                    "uuid": "8280a40f-2a0d-4f90-ba32-4d88ce6c2101",
                },
                {
                    "uuid": "d283e8fe-b7dd-412f-b4a6-b7353a3af2cf",
                    "actions": [
                        {
                            "uuid": "87b83fbb-e421-4742-b572-4323d5cfbf09",
                            "headers": {
                                "Accept": "application/json",
                                "Authorization": "Token @trigger.params.token",
                                "Content-Type": "application/json",
                            },
                            "type": "call_webhook",
                            "url": "@trigger.params.webhook_url",
                            "body": '@(json(object(\n  "contact", object(\n    "uuid", contact.uuid, \n    "name", contact.name, \n    "urn", contact.urn\n  ),\n  "flow", object(\n    "uuid", run.flow.uuid, \n    "name", run.flow.name\n  ),\n  "room", trigger.params.room,\n  "rating", results.avaliacao.value\n)))',
                            "method": "POST",
                            "result_name": "Result",
                        }
                    ],
                    "router": {
                        "type": "switch",
                        "operand": "@results.result.category",
                        "cases": [
                            {
                                "uuid": "deb322f9-13c8-43de-92ba-a2ad6a122838",
                                "type": "has_only_text",
                                "arguments": ["Success"],
                                "category_uuid": "27a7593f-bf49-44e1-8816-a308ffa0d8b4",
                            }
                        ],
                        "categories": [
                            {
                                "uuid": "27a7593f-bf49-44e1-8816-a308ffa0d8b4",
                                "name": "Success",
                                "exit_uuid": "3134a01b-d590-40cd-94b5-d4983e0ab1bd",
                            },
                            {
                                "uuid": "9f3d7a78-e27d-4aac-b594-fe1488c615db",
                                "name": "Failure",
                                "exit_uuid": "bee845df-4a73-430f-adbe-176cf0842a35",
                            },
                        ],
                        "default_category_uuid": "9f3d7a78-e27d-4aac-b594-fe1488c615db",
                    },
                    "exits": [
                        {
                            "uuid": "3134a01b-d590-40cd-94b5-d4983e0ab1bd",
                            "destination_uuid": "c0339434-f9d6-4f51-ad06-9067dc59a379",
                        },
                        {
                            "uuid": "bee845df-4a73-430f-adbe-176cf0842a35",
                            "destination_uuid": "c0339434-f9d6-4f51-ad06-9067dc59a379",
                        },
                    ],
                },
                {
                    "actions": [
                        {
                            "attachments": [],
                            "quick_replies": [],
                            "text": "Deixe um coment\u00e1rio sobre sua experi\u00eancia com nosso atendimento \u270d\ufe0f",
                            "type": "send_msg",
                            "uuid": "173c606e-982b-4089-971a-431693ef3d70",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "9c254d9b-958c-4168-9762-06d6662f8f4f",
                            "uuid": "5f267998-12a4-46af-b029-02a85857ad9a",
                        }
                    ],
                    "uuid": "7edf7591-106c-4587-a5a7-dcbf10d58524",
                },
                {
                    "actions": [],
                    "exits": [
                        {
                            "destination_uuid": "5566fb83-a3a8-4397-ba09-a6b8ff342726",
                            "uuid": "d4f943e3-4a00-4159-8d38-a0636bb9ff00",
                        },
                        {
                            "destination_uuid": "ad315551-2f8d-459f-8667-a245ac11bcd6",
                            "uuid": "8ebed75a-357a-4ceb-9efa-fe50be32d9f2",
                        },
                    ],
                    "router": {
                        "cases": [],
                        "categories": [
                            {
                                "exit_uuid": "d4f943e3-4a00-4159-8d38-a0636bb9ff00",
                                "name": "All Responses",
                                "uuid": "382213ae-a53c-4041-8167-3216ec84aa0e",
                            },
                            {
                                "exit_uuid": "8ebed75a-357a-4ceb-9efa-fe50be32d9f2",
                                "name": "No Response",
                                "uuid": "aabe1606-3199-4503-9454-c5df236d2c9f",
                            },
                        ],
                        "default_category_uuid": "382213ae-a53c-4041-8167-3216ec84aa0e",
                        "operand": "@input.text",
                        "result_name": "comentario",
                        "type": "switch",
                        "wait": {
                            "timeout": {
                                "category_uuid": "aabe1606-3199-4503-9454-c5df236d2c9f",
                                "seconds": 600,
                            },
                            "type": "msg",
                        },
                    },
                    "uuid": "9c254d9b-958c-4168-9762-06d6662f8f4f",
                },
                {
                    "actions": [
                        {
                            "attachments": [],
                            "quick_replies": [],
                            "text": "Deixe um coment\u00e1rio para sempre melhorarmos nosso atendimento \u270d\ufe0f",
                            "type": "send_msg",
                            "uuid": "cff06c3e-435c-488f-a594-ae102633c14d",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "103d35ae-b506-47db-8ffe-2a00c74d469e",
                            "uuid": "18fcd565-83c0-4916-a35b-c9bdb8a55d9f",
                        }
                    ],
                    "uuid": "c0339434-f9d6-4f51-ad06-9067dc59a379",
                },
                {
                    "actions": [],
                    "exits": [
                        {
                            "destination_uuid": "feeb9c96-e9bc-496f-a825-78dca2c02853",
                            "uuid": "c2bcbf0b-c17a-46ac-bbd0-73b414e82bc5",
                        },
                        {
                            "destination_uuid": "168b3d89-6403-479c-b662-9f91e9c36688",
                            "uuid": "3fbcbd94-8d72-41b9-bbe4-6653152f6e1c",
                        },
                    ],
                    "router": {
                        "cases": [],
                        "categories": [
                            {
                                "exit_uuid": "c2bcbf0b-c17a-46ac-bbd0-73b414e82bc5",
                                "name": "All Responses",
                                "uuid": "962833a3-6da9-4c0d-8d99-73814713b1a5",
                            },
                            {
                                "exit_uuid": "3fbcbd94-8d72-41b9-bbe4-6653152f6e1c",
                                "name": "No Response",
                                "uuid": "f60ea031-b882-40ee-88bb-1209ecf58857",
                            },
                        ],
                        "default_category_uuid": "962833a3-6da9-4c0d-8d99-73814713b1a5",
                        "operand": "@input.text",
                        "result_name": "comentario",
                        "type": "switch",
                        "wait": {
                            "timeout": {
                                "category_uuid": "f60ea031-b882-40ee-88bb-1209ecf58857",
                                "seconds": 600,
                            },
                            "type": "msg",
                        },
                    },
                    "uuid": "103d35ae-b506-47db-8ffe-2a00c74d469e",
                },
                {
                    "actions": [
                        {
                            "attachments": [],
                            "quick_replies": [],
                            "text": "Seu atendimento foi finalizado.\n\nAgradecemos a sua colabora\u00e7\u00e3o. At\u00e9 a pr\u00f3xima \ud83d\udc4b",
                            "type": "send_msg",
                            "uuid": "4cd3777a-369d-408b-8625-8335c1cf01fa",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "611f05e2-eb39-4a86-a4ab-2ed93fc602b0",
                            "uuid": "bd1dada6-7170-450d-8359-ff8a1c99fbf1",
                        }
                    ],
                    "uuid": "5566fb83-a3a8-4397-ba09-a6b8ff342726",
                },
                {
                    "actions": [
                        {
                            "category": "N\u00e3o respondente",
                            "name": "comentario",
                            "type": "set_run_result",
                            "uuid": "7a0ae39e-860f-47ae-b21b-e1b54ed531cd",
                            "value": "N\u00e3o respondente",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "611f05e2-eb39-4a86-a4ab-2ed93fc602b0",
                            "uuid": "1a90cd2d-8322-48f5-8012-ff710056e3ca",
                        }
                    ],
                    "uuid": "ad315551-2f8d-459f-8667-a245ac11bcd6",
                },
                {
                    "actions": [
                        {
                            "attachments": [],
                            "quick_replies": [],
                            "text": "Seu atendimento foi finalizado. Iremos analisar seu coment\u00e1rio com responsabilidade. \n\nAgradecemos a sua colabora\u00e7\u00e3o para melhorar o atendimento. At\u00e9 a pr\u00f3xima \ud83d\udc4b",
                            "type": "send_msg",
                            "uuid": "0bae029f-1337-4a60-bc8a-9198b3e32fc8",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "611f05e2-eb39-4a86-a4ab-2ed93fc602b0",
                            "uuid": "c2113a99-33e6-4be1-8084-b6d7cd5dd3b3",
                        }
                    ],
                    "uuid": "feeb9c96-e9bc-496f-a825-78dca2c02853",
                },
                {
                    "actions": [
                        {
                            "category": "N\u00e3o respondente",
                            "name": "comentario",
                            "type": "set_run_result",
                            "uuid": "cb274102-7a5e-421c-9690-4a79311f2bd3",
                            "value": "N\u00e3o respondente",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "611f05e2-eb39-4a86-a4ab-2ed93fc602b0",
                            "uuid": "5ae03567-56a0-4568-895f-a89f22e11a4f",
                        }
                    ],
                    "uuid": "168b3d89-6403-479c-b662-9f91e9c36688",
                },
                {
                    "actions": [
                        {
                            "body": '@(json(object(\n  "contact", object(\n    "uuid", contact.uuid, \n    "name", contact.name, \n    "urn", contact.urn\n  ),\n  "flow", object(\n    "uuid", run.flow.uuid, \n    "name", run.flow.name\n  ),\n  "room", trigger.params.room,\n  "rating", results.avaliacao.value,\n  "comment", results.comentario.value\n)))',
                            "headers": {
                                "Accept": "application/json",
                                "Authorization": "Token @trigger.params.token",
                                "Content-Type": "application/json",
                            },
                            "method": "POST",
                            "result_name": "Result",
                            "type": "call_webhook",
                            "url": "@trigger.params.webhook_url",
                            "uuid": "9c18f933-81e7-429e-8e4f-42f2cb073f97",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": None,
                            "uuid": "37f3967b-1b4e-41ec-bc6e-8c252a915fc2",
                        },
                        {
                            "destination_uuid": None,
                            "uuid": "b90c56d9-4933-4125-892a-8cb0f96628bb",
                        },
                    ],
                    "router": {
                        "cases": [
                            {
                                "arguments": ["Success"],
                                "category_uuid": "fbc4a3d8-3f14-4ba3-8f51-2b7443ed2e89",
                                "type": "has_only_text",
                                "uuid": "b21bd815-8c56-4f0f-8505-0aff7b4f2b76",
                            }
                        ],
                        "categories": [
                            {
                                "exit_uuid": "37f3967b-1b4e-41ec-bc6e-8c252a915fc2",
                                "name": "Success",
                                "uuid": "fbc4a3d8-3f14-4ba3-8f51-2b7443ed2e89",
                            },
                            {
                                "exit_uuid": "b90c56d9-4933-4125-892a-8cb0f96628bb",
                                "name": "Failure",
                                "uuid": "931a4759-cd06-4498-9ece-9dec1c1a7b25",
                            },
                        ],
                        "default_category_uuid": "931a4759-cd06-4498-9ece-9dec1c1a7b25",
                        "operand": "@results.result.category",
                        "type": "switch",
                    },
                    "uuid": "611f05e2-eb39-4a86-a4ab-2ed93fc602b0",
                },
            ],
            "spec_version": "13.1.0",
            "type": "messaging",
            "uuid": "f343c55d-f43d-41be-9002-f12439d52b25",
            "revision": 36,
        }
    ],
    "campaigns": [],
    "triggers": [],
    "fields": [
        {
            "key": "nota_pesquisa_atendimento_humano",
            "name": "Nota Pesquisa Atendimento Humano",
            "type": "text",
        }
    ],
    "groups": [],
}
