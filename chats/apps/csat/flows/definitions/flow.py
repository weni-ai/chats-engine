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
                    "0fa75334-f5e3-42c7-96c4-8fa90dd49253": {
                        "position": {
                            "left": "1215.3460900709856",
                            "top": "3401.4251190743635",
                        },
                        "type": "execute_actions",
                    },
                    "1d2b9b30-21a8-4228-80fe-c72c2c270f59": {
                        "config": {},
                        "position": {
                            "left": "908.7015043077097",
                            "top": "3790.3354566551607",
                        },
                        "type": "split_by_webhook",
                    },
                    "2996a5f5-c514-4aac-8611-d45184f41dff": {
                        "config": {"cases": {}},
                        "position": {
                            "left": "525.4199459661597",
                            "top": "2963.3440877475277",
                        },
                        "type": "wait_for_response",
                    },
                    "33244906-ad00-43a5-bbcc-1261eb56908f": {
                        "config": {},
                        "position": {
                            "left": "1248.6657730270365",
                            "top": "2682.993941290002",
                        },
                        "type": "split_by_webhook",
                    },
                    "45cce649-432a-4fba-950b-44ef62aa231e": {
                        "position": {"left": 521, "top": 2346},
                        "type": "execute_actions",
                    },
                    "667e0b52-44b2-42fb-b12a-a443da293377": {
                        "position": {
                            "left": "1243.6657730270365",
                            "top": "2384.993941290002",
                        },
                        "type": "execute_actions",
                    },
                    "6e193b75-8607-4f15-bdee-6c0ffdcb2eea": {
                        "position": {
                            "left": "1537.7174976978713",
                            "top": "1645.4129353706592",
                        },
                        "type": "execute_actions",
                    },
                    "6f66e98e-5192-469a-8a26-e38b16ef6e7c": {
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
                    "89dbc585-8951-4387-b224-478877bfacec": {
                        "config": {"cases": {}},
                        "position": {
                            "left": "1262.3460900709856",
                            "top": "3166.571929565236",
                        },
                        "type": "wait_for_response",
                    },
                    "9ddb6ec6-4415-492d-b7ad-185e1df58f5f": {
                        "position": {
                            "left": "796.927464564468",
                            "top": "3224.6395402223325",
                        },
                        "type": "execute_actions",
                    },
                    "a5a341a4-fba8-4d7a-84d2-ffa854b5c584": {
                        "position": {
                            "left": "1341.074049511356",
                            "top": "1219.275597947668",
                        },
                        "type": "execute_actions",
                    },
                    "a62c143f-2b14-4cd1-bf54-4d1a0d7208a3": {
                        "position": {
                            "left": "516.5389376101214",
                            "top": "2184.638408866735",
                        },
                        "type": "execute_actions",
                    },
                    "a6c84c5f-0741-4940-8e68-dc6f6f1a6f55": {
                        "position": {
                            "left": "1135.002130439344",
                            "top": "1644.0453112453636",
                        },
                        "type": "execute_actions",
                    },
                    "a99aeea2-cd50-4dc4-9d13-d3e0e8469ed8": {
                        "config": {"cases": {}},
                        "position": {
                            "left": "1157.2408609900526",
                            "top": "2031.653596440618",
                        },
                        "type": "wait_for_response",
                    },
                    "b4d5b917-bef0-449e-b616-90e3b01a4c3d": {
                        "position": {
                            "left": "1245.9127841724944",
                            "top": "2969.993941290002",
                        },
                        "type": "execute_actions",
                    },
                    "d14d6624-4480-4a2b-9944-4f011168df28": {
                        "config": {"cases": {}},
                        "position": {
                            "left": "1344.7429126871152",
                            "top": "1474.275597947668",
                        },
                        "type": "split_by_scheme",
                    },
                    "d1ce842b-7a72-4d43-8f6b-5c66a2f23d30": {
                        "position": {"left": "531.1525515926652", "top": 2784},
                        "type": "execute_actions",
                    },
                    "e19f620f-0ba1-4087-aff7-01bd374689f4": {
                        "position": {
                            "left": "1479.7303603839714",
                            "top": "3403.84381983449",
                        },
                        "type": "execute_actions",
                    },
                    "f2b1a441-8a0f-4647-ac35-990a43b44bb2": {
                        "config": {},
                        "position": {"left": "530.5389376101214", "top": 2563},
                        "type": "split_by_webhook",
                    },
                    "f3e02943-99a5-4e87-9a9c-722ef5a92d9b": {
                        "position": {
                            "left": "2102.730635385634",
                            "top": "1864.5697418429131",
                        },
                        "type": "execute_actions",
                    },
                    "f9375a98-1ce1-4b4e-bc8c-a616ce53d4fe": {
                        "position": {
                            "left": "476.41994596615973",
                            "top": "3216.3440877475277",
                        },
                        "type": "execute_actions",
                    },
                },
                "stickies": {},
            },
            "expire_after_minutes": 10080,
            "integrations": {"classifiers": [], "ticketers": []},
            "language": "base",
            "localization": {
                "eng": {
                    "054ccf87-574a-4cc0-b99a-3782eaa186cc": {
                        "arguments": ["neutral normal ok"]
                    },
                    "0ec303b2-48a1-429b-8a85-92d4d8095e31": {
                        "arguments": ["Very satisfied \ud83d\ude03"]
                    },
                    "2374cb9b-48dc-496f-9c6e-8eeafe773095": {
                        "arguments": ["terrible horrible"]
                    },
                    "3af769e4-6def-4df0-950b-396f757409fd": {
                        "button_text": ["Select here"],
                        "footer": [
                            "It\u2019s very quick, it won\u2019t even take a minute."
                        ],
                        "header_text": ["Customer Satisfaction Survey"],
                        "quick_replies": [],
                        "text": ["*How would you rate my service?* \ud83d\udc47"],
                    },
                    "3b2422cf-f205-40a4-8f54-dbed1d900082": {
                        "arguments": ["Satisfied \ud83d\ude42"]
                    },
                    "53e6eba4-26a7-4eba-b632-b4f5c532d4ba": {
                        "attachments": [],
                        "text": [
                            "Your session has ended.\n\nThank you for your feedback. See you next time! \ud83d\udc4b"
                        ],
                    },
                    "6054cb80-ee48-4208-8914-a6083991e062": {
                        "attachments": [],
                        "quick_replies": [
                            "Very dissatisfied \ud83d\ude23",
                            "Dissatisfied \ud83d\ude41",
                            "Neutral \ud83d\ude36",
                            "Satisfied \ud83d\ude42",
                            "Very satisfied \ud83d\ude03",
                        ],
                        "text": ["**How would you rate my service?** \ud83d\udc47"],
                    },
                    "75f4674d-59b0-4ecf-8593-12bb2243a775": {
                        "description": [""],
                        "title": ["Neutral \ud83d\ude36"],
                    },
                    "7ad37f79-95bd-40e3-ba65-2b1c60ed49bc": {"arguments": ["bad poor"]},
                    "8f98f7fb-5b5c-46f2-b5a4-7cf56f6de47f": {
                        "arguments": ["Very dissatisfied \ud83d\ude23"]
                    },
                    "9047d9b8-2a2c-4243-873b-d67d59b125bd": {
                        "description": [""],
                        "title": ["Satisfied \ud83d\ude42"],
                    },
                    "91654f20-7dfd-4adb-a92c-a284ab9b88f1": {"arguments": ["good"]},
                    "9f65705f-44cc-4458-bf0f-e265a2453576": {
                        "arguments": ["Dissatisfied \ud83d\ude41"]
                    },
                    "a531714c-11da-428a-91c4-037d578f9462": {
                        "attachments": [],
                        "text": [
                            "Before continuing, could you please answer our survey below?"
                        ],
                    },
                    "b5592521-3d93-4422-8262-a49c0a02382a": {
                        "attachments": [],
                        "text": [
                            "Your session has ended. We will carefully review your feedback.\n\nThank you for helping us improve our service. See you next time! \ud83d\udc4b"
                        ],
                    },
                    "be1b597f-6f03-4f59-9dcb-d0c71acc9aaa": {
                        "arguments": ["satisfied"]
                    },
                    "c14d5459-ff98-4b17-b47f-eeaa9b4e1d03": {"arguments": ["great"]},
                    "d3046aa6-f108-4d3b-95d3-5345e9a79f18": {
                        "description": [""],
                        "title": ["Very dissatisfied \ud83d\ude23"],
                    },
                    "d594fc0f-92f0-4ace-ac70-5a4e4c09eda4": {
                        "arguments": ["Neutral \ud83d\ude36"]
                    },
                    "d6087f51-065f-442b-bf84-53ba2cfe8754": {
                        "attachments": [],
                        "text": [
                            "Leave a comment so we can keep improving our service \u270d\ufe0f"
                        ],
                    },
                    "e4ae4119-afa9-4a67-a347-c35bcd49a083": {
                        "attachments": [],
                        "text": [
                            "Leave a comment about your experience with our service \u270d\ufe0f"
                        ],
                    },
                    "f6689156-1c37-4587-9ca5-b519a8d9a401": {
                        "description": [""],
                        "title": ["Very satisfied \ud83d\ude03"],
                    },
                    "fe130649-4a90-4d08-9863-9447755618f8": {
                        "description": [""],
                        "title": ["Dissatisfied \ud83d\ude41"],
                    },
                },
                "por": {
                    "3af769e4-6def-4df0-950b-396f757409fd": {
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
                    "53e6eba4-26a7-4eba-b632-b4f5c532d4ba": {
                        "attachments": [],
                        "text": [
                            "Seu atendimento foi finalizado.\n\nAgradecemos a sua colabora\u00e7\u00e3o. At\u00e9 a pr\u00f3xima \ud83d\udc4b"
                        ],
                    },
                    "6054cb80-ee48-4208-8914-a6083991e062": {
                        "attachments": [],
                        "text": [
                            "**Como voc\u00ea avalia o meu atendimento?** \ud83d\udc47"
                        ],
                    },
                    "75f4674d-59b0-4ecf-8593-12bb2243a775": {
                        "description": [""],
                        "title": ["Neutro \ud83d\ude36"],
                    },
                    "9047d9b8-2a2c-4243-873b-d67d59b125bd": {
                        "description": [""],
                        "title": ["Satisfeito \ud83d\ude42"],
                    },
                    "a531714c-11da-428a-91c4-037d578f9462": {
                        "attachments": [],
                        "text": [
                            "Antes de continuar, poderia responder nossa pesquisa abaixo?"
                        ],
                    },
                    "b5592521-3d93-4422-8262-a49c0a02382a": {
                        "attachments": [],
                        "text": [
                            "Seu atendimento foi finalizado. Iremos analisar seu coment\u00e1rio com responsabilidade.\n\nAgradecemos a sua colabora\u00e7\u00e3o para melhorar o atendimento. At\u00e9 a pr\u00f3xima \ud83d\udc4b"
                        ],
                    },
                    "d3046aa6-f108-4d3b-95d3-5345e9a79f18": {
                        "description": [""],
                        "title": ["Muito insatisfeito \ud83d\ude23"],
                    },
                    "d6087f51-065f-442b-bf84-53ba2cfe8754": {
                        "attachments": [],
                        "text": [
                            "Deixe um coment\u00e1rio para sempre melhorarmos nosso atendimento \u270d\ufe0f"
                        ],
                    },
                    "e4ae4119-afa9-4a67-a347-c35bcd49a083": {
                        "attachments": [],
                        "text": [
                            "Deixe um coment\u00e1rio sobre sua experi\u00eancia com nosso atendimento \u270d\ufe0f"
                        ],
                    },
                    "f6689156-1c37-4587-9ca5-b519a8d9a401": {
                        "description": [""],
                        "title": ["Muito satisfeito \ud83d\ude03"],
                    },
                    "fe130649-4a90-4d08-9863-9447755618f8": {
                        "description": [""],
                        "title": ["Insatisfeito \ud83d\ude41"],
                    },
                },
                "spa": {
                    "054ccf87-574a-4cc0-b99a-3782eaa186cc": {
                        "arguments": ["normal neutral"]
                    },
                    "0ec303b2-48a1-429b-8a85-92d4d8095e31": {
                        "arguments": ["Muy satisfecho \ud83d\ude03"]
                    },
                    "2374cb9b-48dc-496f-9c6e-8eeafe773095": {
                        "arguments": ["horrible terrible"]
                    },
                    "3af769e4-6def-4df0-950b-396f757409fd": {
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
                    "3b2422cf-f205-40a4-8f54-dbed1d900082": {
                        "arguments": ["Satisfecho \ud83d\ude42"]
                    },
                    "53e6eba4-26a7-4eba-b632-b4f5c532d4ba": {
                        "attachments": [],
                        "text": [
                            "Tu atenci\u00f3n ha finalizado.\n\nAgradecemos tu colaboraci\u00f3n. \u00a1Hasta la pr\u00f3xima! \ud83d\udc4b"
                        ],
                    },
                    "6054cb80-ee48-4208-8914-a6083991e062": {
                        "attachments": [],
                        "quick_replies": [
                            "Muy insatisfecho \ud83d\ude23",
                            "Insatisfecho \ud83d\ude41",
                            "Neutral \ud83d\ude36",
                            "Satisfecho \ud83d\ude42",
                            "Muy satisfecho \ud83d\ude03",
                        ],
                        "text": [
                            "**\u00bfC\u00f3mo valoras mi atenci\u00f3n?** \ud83d\udc47"
                        ],
                    },
                    "75f4674d-59b0-4ecf-8593-12bb2243a775": {
                        "description": [""],
                        "title": ["Neutral \ud83d\ude36"],
                    },
                    "7ad37f79-95bd-40e3-ba65-2b1c60ed49bc": {
                        "arguments": ["malo mala"]
                    },
                    "8f98f7fb-5b5c-46f2-b5a4-7cf56f6de47f": {
                        "arguments": ["Muy insatisfecho \ud83d\ude23"]
                    },
                    "9047d9b8-2a2c-4243-873b-d67d59b125bd": {
                        "description": [""],
                        "title": ["Satisfecho \ud83d\ude42"],
                    },
                    "91654f20-7dfd-4adb-a92c-a284ab9b88f1": {
                        "arguments": ["bueno buena"]
                    },
                    "9f65705f-44cc-4458-bf0f-e265a2453576": {
                        "arguments": ["Insatisfecho \ud83d\ude41"]
                    },
                    "a531714c-11da-428a-91c4-037d578f9462": {
                        "attachments": [],
                        "text": [
                            "Antes de continuar, \u00bfpodr\u00edas responder a nuestra encuesta de abajo?"
                        ],
                    },
                    "b5592521-3d93-4422-8262-a49c0a02382a": {
                        "attachments": [],
                        "text": [
                            "Tu atenci\u00f3n ha finalizado. Analizaremos tu comentario con responsabilidad.\n\nGracias por ayudarnos a mejorar nuestra atenci\u00f3n. \u00a1Hasta la pr\u00f3xima! \ud83d\udc4b"
                        ],
                    },
                    "be1b597f-6f03-4f59-9dcb-d0c71acc9aaa": {
                        "arguments": ["satisfecho satisfecha"]
                    },
                    "c14d5459-ff98-4b17-b47f-eeaa9b4e1d03": {
                        "arguments": ["excelente"]
                    },
                    "d3046aa6-f108-4d3b-95d3-5345e9a79f18": {
                        "description": [""],
                        "title": ["Muy insatisfecho \ud83d\ude23"],
                    },
                    "d594fc0f-92f0-4ace-ac70-5a4e4c09eda4": {
                        "arguments": ["Neutral \ud83d\ude36"]
                    },
                    "d6087f51-065f-442b-bf84-53ba2cfe8754": {
                        "attachments": [],
                        "text": [
                            "D\u00e9janos un comentario para que podamos seguir mejorando nuestra atenci\u00f3n \u270d\ufe0f"
                        ],
                    },
                    "e4ae4119-afa9-4a67-a347-c35bcd49a083": {
                        "attachments": [],
                        "text": [
                            "D\u00e9janos un comentario sobre tu experiencia con nuestra atenci\u00f3n \u270d\ufe0f"
                        ],
                    },
                    "f6689156-1c37-4587-9ca5-b519a8d9a401": {
                        "description": [""],
                        "title": ["Muy satisfecho \ud83d\ude03"],
                    },
                    "fe130649-4a90-4d08-9863-9447755618f8": {
                        "description": [""],
                        "title": ["Insatisfecho \ud83d\ude41"],
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
                            "uuid": "134a9386-e729-42e4-9273-e7b3eed764ee",
                            "value": "0",
                        },
                        {
                            "attachments": [],
                            "quick_replies": [],
                            "text": "Antes de encerrar, conte como foi sua experi\u00eancia!",
                            "type": "send_msg",
                            "uuid": "2311d79a-f10c-4631-9a5e-904edb770897",
                        },
                    ],
                    "exits": [
                        {
                            "destination_uuid": "d14d6624-4480-4a2b-9944-4f011168df28",
                            "uuid": "9519306d-5ea6-4306-9c14-c986f9bfe293",
                        }
                    ],
                    "uuid": "a5a341a4-fba8-4d7a-84d2-ffa854b5c584",
                },
                {
                    "actions": [],
                    "exits": [
                        {
                            "destination_uuid": "a6c84c5f-0741-4940-8e68-dc6f6f1a6f55",
                            "uuid": "acfe0725-1a42-4f23-ae49-f536d172c97d",
                        },
                        {
                            "destination_uuid": "6e193b75-8607-4f15-bdee-6c0ffdcb2eea",
                            "uuid": "58e753b8-b102-41fa-9e5f-c5b8b6d67e97",
                        },
                    ],
                    "router": {
                        "cases": [
                            {
                                "arguments": ["whatsapp"],
                                "category_uuid": "2e8e5193-742d-4984-8182-015d758dd9fa",
                                "type": "has_only_phrase",
                                "uuid": "4d17a7a5-2cf0-4714-8548-98840018f13b",
                            }
                        ],
                        "categories": [
                            {
                                "exit_uuid": "acfe0725-1a42-4f23-ae49-f536d172c97d",
                                "name": "WhatsApp",
                                "uuid": "2e8e5193-742d-4984-8182-015d758dd9fa",
                            },
                            {
                                "exit_uuid": "58e753b8-b102-41fa-9e5f-c5b8b6d67e97",
                                "name": "Other",
                                "uuid": "f192cff2-9201-4782-a5a9-e822b74aad79",
                            },
                        ],
                        "default_category_uuid": "f192cff2-9201-4782-a5a9-e822b74aad79",
                        "operand": "@(urn_parts(contact.urn).scheme)",
                        "result_name": "",
                        "type": "switch",
                    },
                    "uuid": "d14d6624-4480-4a2b-9944-4f011168df28",
                },
                {
                    "actions": [
                        {
                            "button_text": "Selecione aqui",
                            "flow_data_attachment_name_map": {},
                            "footer": "\u00c9 bem r\u00e1pido, n\u00e3o vai demorar nem 1 minuto.",
                            "header_text": "Pesquisa de Satisfa\u00e7\u00e3o",
                            "header_type": "text",
                            "interaction_type": "list",
                            "list_items": [
                                {
                                    "description": "",
                                    "title": "Muito insatisfeito \ud83d\ude23",
                                    "uuid": "d3046aa6-f108-4d3b-95d3-5345e9a79f18",
                                },
                                {
                                    "description": "",
                                    "title": "Insatisfeito \ud83d\ude41",
                                    "uuid": "fe130649-4a90-4d08-9863-9447755618f8",
                                },
                                {
                                    "description": "",
                                    "title": "Neutro \ud83d\ude36",
                                    "uuid": "75f4674d-59b0-4ecf-8593-12bb2243a775",
                                },
                                {
                                    "description": "",
                                    "title": "Satisfeito \ud83d\ude42",
                                    "uuid": "9047d9b8-2a2c-4243-873b-d67d59b125bd",
                                },
                                {
                                    "description": "",
                                    "title": "Muito satisfeito \ud83d\ude03",
                                    "uuid": "f6689156-1c37-4587-9ca5-b519a8d9a401",
                                },
                            ],
                            "messageType": "interactive",
                            "quick_replies": [],
                            "text": "*Como voc\u00ea avalia o meu atendimento?* \ud83d\udc47",
                            "type": "send_whatsapp_msg",
                            "uuid": "3af769e4-6def-4df0-950b-396f757409fd",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "a99aeea2-cd50-4dc4-9d13-d3e0e8469ed8",
                            "uuid": "f7f845f1-cff8-4fab-b9c3-7fe92027cd82",
                        }
                    ],
                    "uuid": "a6c84c5f-0741-4940-8e68-dc6f6f1a6f55",
                },
                {
                    "actions": [
                        {
                            "attachments": [],
                            "quick_replies": [
                                "Muito insatisfeito \ud83d\ude23",
                                "Insatisfeito \ud83d\ude41",
                                "Neutro \ud83d\ude36",
                                "Satisfeito \ud83d\ude42",
                                "Muito satisfeito \ud83d\ude03",
                            ],
                            "text": "**Como voc\u00ea avalia o meu atendimento?** \ud83d\udc47",
                            "type": "send_msg",
                            "uuid": "6054cb80-ee48-4208-8914-a6083991e062",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "a99aeea2-cd50-4dc4-9d13-d3e0e8469ed8",
                            "uuid": "7b67e90d-114a-49f7-8843-772a9f6b9df9",
                        }
                    ],
                    "uuid": "6e193b75-8607-4f15-bdee-6c0ffdcb2eea",
                },
                {
                    "actions": [
                        {
                            "attachments": [],
                            "quick_replies": [],
                            "text": "Sua opini\u00e3o \u00e9 muito importante para n\u00f3s e leva menos de 1 minuto. Agradecemos se puder responder.",
                            "type": "send_msg",
                            "uuid": "a531714c-11da-428a-91c4-037d578f9462",
                        },
                        {
                            "category": "",
                            "name": "tentativa",
                            "type": "set_run_result",
                            "uuid": "6c9debde-1f30-427f-92b4-e0489a9cd390",
                            "value": "@(results.tentativa +1)",
                        },
                    ],
                    "exits": [
                        {
                            "destination_uuid": "d14d6624-4480-4a2b-9944-4f011168df28",
                            "uuid": "af57b673-2b23-4209-844e-660925eaaae4",
                        }
                    ],
                    "uuid": "f3e02943-99a5-4e87-9a9c-722ef5a92d9b",
                },
                {
                    "actions": [],
                    "exits": [
                        {
                            "destination_uuid": "a62c143f-2b14-4cd1-bf54-4d1a0d7208a3",
                            "uuid": "346ad7dd-1e9f-47c3-8e23-59bea0d004a7",
                        },
                        {
                            "destination_uuid": "a62c143f-2b14-4cd1-bf54-4d1a0d7208a3",
                            "uuid": "c545980a-e542-43dc-9f02-cec4e0f3bcbe",
                        },
                        {
                            "destination_uuid": "667e0b52-44b2-42fb-b12a-a443da293377",
                            "uuid": "ce875e24-ad2f-4815-9d68-8960e767a494",
                        },
                        {
                            "destination_uuid": "667e0b52-44b2-42fb-b12a-a443da293377",
                            "uuid": "0697fa2b-567c-4d3c-854c-b41c8b8e0d90",
                        },
                        {
                            "destination_uuid": "667e0b52-44b2-42fb-b12a-a443da293377",
                            "uuid": "5791fd9d-3285-4eaf-a342-1e0698fff6c8",
                        },
                        {
                            "destination_uuid": "6f66e98e-5192-469a-8a26-e38b16ef6e7c",
                            "uuid": "f42ff2b8-45fb-47eb-b401-6919de7d6a0c",
                        },
                        {
                            "destination_uuid": "6f66e98e-5192-469a-8a26-e38b16ef6e7c",
                            "uuid": "764b9ca1-bafc-4473-b4ea-015b4ed53c87",
                        },
                    ],
                    "router": {
                        "cases": [
                            {
                                "arguments": ["Muito satisfeito \ud83d\ude03"],
                                "category_uuid": "e79ef5e4-c191-4eff-a401-da0285274dca",
                                "type": "has_only_phrase",
                                "uuid": "0ec303b2-48a1-429b-8a85-92d4d8095e31",
                            },
                            {
                                "arguments": ["Satisfeito \ud83d\ude42"],
                                "category_uuid": "247b7078-2464-4eae-a6ed-8a9425e67e9a",
                                "type": "has_only_phrase",
                                "uuid": "3b2422cf-f205-40a4-8f54-dbed1d900082",
                            },
                            {
                                "arguments": ["Neutro \ud83d\ude36"],
                                "category_uuid": "8e689235-e3cd-4a60-b3b4-1d919a78cea7",
                                "type": "has_only_phrase",
                                "uuid": "d594fc0f-92f0-4ace-ac70-5a4e4c09eda4",
                            },
                            {
                                "arguments": ["Insatisfeito \ud83d\ude41"],
                                "category_uuid": "e01f83e7-a340-4867-a964-ec2032bf9f91",
                                "type": "has_only_phrase",
                                "uuid": "9f65705f-44cc-4458-bf0f-e265a2453576",
                            },
                            {
                                "arguments": ["Muito insatisfeito \ud83d\ude23"],
                                "category_uuid": "e81646c0-5ef8-425a-a700-346d8f7e67be",
                                "type": "has_only_phrase",
                                "uuid": "8f98f7fb-5b5c-46f2-b5a4-7cf56f6de47f",
                            },
                            {
                                "arguments": ["\u00f3timo otimo"],
                                "category_uuid": "e79ef5e4-c191-4eff-a401-da0285274dca",
                                "type": "has_any_word",
                                "uuid": "c14d5459-ff98-4b17-b47f-eeaa9b4e1d03",
                            },
                            {
                                "arguments": ["bom boa"],
                                "category_uuid": "247b7078-2464-4eae-a6ed-8a9425e67e9a",
                                "type": "has_any_word",
                                "uuid": "91654f20-7dfd-4adb-a92c-a284ab9b88f1",
                            },
                            {
                                "arguments": ["neutro neutra normal"],
                                "category_uuid": "8e689235-e3cd-4a60-b3b4-1d919a78cea7",
                                "type": "has_any_word",
                                "uuid": "054ccf87-574a-4cc0-b99a-3782eaa186cc",
                            },
                            {
                                "arguments": ["ruim rum"],
                                "category_uuid": "e01f83e7-a340-4867-a964-ec2032bf9f91",
                                "type": "has_any_word",
                                "uuid": "7ad37f79-95bd-40e3-ba65-2b1c60ed49bc",
                            },
                            {
                                "arguments": ["p\u00e9ssimo pessimo pesimo"],
                                "category_uuid": "e81646c0-5ef8-425a-a700-346d8f7e67be",
                                "type": "has_any_word",
                                "uuid": "2374cb9b-48dc-496f-9c6e-8eeafe773095",
                            },
                            {
                                "arguments": ["satisfeito satisfeita"],
                                "category_uuid": "247b7078-2464-4eae-a6ed-8a9425e67e9a",
                                "type": "has_any_word",
                                "uuid": "be1b597f-6f03-4f59-9dcb-d0c71acc9aaa",
                            },
                        ],
                        "categories": [
                            {
                                "exit_uuid": "346ad7dd-1e9f-47c3-8e23-59bea0d004a7",
                                "name": "5",
                                "uuid": "e79ef5e4-c191-4eff-a401-da0285274dca",
                            },
                            {
                                "exit_uuid": "c545980a-e542-43dc-9f02-cec4e0f3bcbe",
                                "name": "4",
                                "uuid": "247b7078-2464-4eae-a6ed-8a9425e67e9a",
                            },
                            {
                                "exit_uuid": "ce875e24-ad2f-4815-9d68-8960e767a494",
                                "name": "3",
                                "uuid": "8e689235-e3cd-4a60-b3b4-1d919a78cea7",
                            },
                            {
                                "exit_uuid": "0697fa2b-567c-4d3c-854c-b41c8b8e0d90",
                                "name": "2",
                                "uuid": "e01f83e7-a340-4867-a964-ec2032bf9f91",
                            },
                            {
                                "exit_uuid": "5791fd9d-3285-4eaf-a342-1e0698fff6c8",
                                "name": "1",
                                "uuid": "e81646c0-5ef8-425a-a700-346d8f7e67be",
                            },
                            {
                                "exit_uuid": "f42ff2b8-45fb-47eb-b401-6919de7d6a0c",
                                "name": "Other",
                                "uuid": "2c20a2e8-71ba-400b-83f3-be6276639607",
                            },
                            {
                                "exit_uuid": "764b9ca1-bafc-4473-b4ea-015b4ed53c87",
                                "name": "No Response",
                                "uuid": "4e54c4d3-53a9-4a1e-bdf3-df84394f8578",
                            },
                        ],
                        "default_category_uuid": "2c20a2e8-71ba-400b-83f3-be6276639607",
                        "operand": "@input.text",
                        "result_name": "avaliacao",
                        "type": "switch",
                        "wait": {
                            "timeout": {
                                "category_uuid": "4e54c4d3-53a9-4a1e-bdf3-df84394f8578",
                                "seconds": 600,
                            },
                            "type": "msg",
                        },
                    },
                    "uuid": "a99aeea2-cd50-4dc4-9d13-d3e0e8469ed8",
                },
                {
                    "actions": [
                        {
                            "field": {
                                "key": "nota_pesquisa_atendimento_humano",
                                "name": "Nota Pesquisa Atendimento Humano",
                            },
                            "type": "set_contact_field",
                            "uuid": "0eda76ae-55ff-47ca-89a4-99d677d6adc2",
                            "value": "@results.avaliacao.category",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "45cce649-432a-4fba-950b-44ef62aa231e",
                            "uuid": "4ca4c07b-f933-4114-a6f5-b39b1a1eb362",
                        }
                    ],
                    "uuid": "a62c143f-2b14-4cd1-bf54-4d1a0d7208a3",
                },
                {
                    "actions": [],
                    "exits": [
                        {
                            "destination_uuid": None,
                            "uuid": "2610af32-46b1-42ba-bf0a-63be60ebe651",
                        },
                        {
                            "destination_uuid": "f3e02943-99a5-4e87-9a9c-722ef5a92d9b",
                            "uuid": "f4f287f5-9bf4-4f61-b63c-7a9e0e16b3b6",
                        },
                    ],
                    "router": {
                        "cases": [
                            {
                                "arguments": ["1"],
                                "category_uuid": "ad6575ec-e5dd-426f-9a7b-b419ef259e68",
                                "type": "has_any_word",
                                "uuid": "b512cc55-c90d-4813-9061-507dccb1b172",
                            }
                        ],
                        "categories": [
                            {
                                "exit_uuid": "2610af32-46b1-42ba-bf0a-63be60ebe651",
                                "name": "J\u00e1 tentou 1x",
                                "uuid": "ad6575ec-e5dd-426f-9a7b-b419ef259e68",
                            },
                            {
                                "exit_uuid": "f4f287f5-9bf4-4f61-b63c-7a9e0e16b3b6",
                                "name": "Other",
                                "uuid": "d1f82e41-961a-41e2-b438-d319e6b19468",
                            },
                        ],
                        "default_category_uuid": "d1f82e41-961a-41e2-b438-d319e6b19468",
                        "operand": "@results.tentativa",
                        "type": "switch",
                    },
                    "uuid": "6f66e98e-5192-469a-8a26-e38b16ef6e7c",
                },
                {
                    "actions": [
                        {
                            "category": "@results.avaliacao.category",
                            "name": "avaliacao",
                            "type": "set_run_result",
                            "uuid": "0a2d8728-7440-4c07-b2f2-ea98f492c773",
                            "value": "@results.avaliacao.category",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "f2b1a441-8a0f-4647-ac35-990a43b44bb2",
                            "uuid": "5d49fedd-92f6-40a5-a92d-022d7d28a466",
                        }
                    ],
                    "uuid": "45cce649-432a-4fba-950b-44ef62aa231e",
                },
                {
                    "actions": [
                        {
                            "field": {
                                "key": "nota_pesquisa_atendimento_humano",
                                "name": "Nota Pesquisa Atendimento Humano",
                            },
                            "type": "set_contact_field",
                            "uuid": "a4b9bf49-feef-421a-9991-946070991196",
                            "value": "@results.avaliacao.category",
                        },
                        {
                            "category": "@results.avaliacao.category",
                            "name": "avaliacao",
                            "type": "set_run_result",
                            "uuid": "3d07e48b-5a04-494d-9cbe-d99f997ce023",
                            "value": "@results.avaliacao.category",
                        },
                    ],
                    "exits": [
                        {
                            "destination_uuid": "33244906-ad00-43a5-bbcc-1261eb56908f",
                            "uuid": "0f4aa105-00f6-44e3-bc0d-8f164e41bcd8",
                        }
                    ],
                    "uuid": "667e0b52-44b2-42fb-b12a-a443da293377",
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
                            "uuid": "466dbcf9-d099-41fd-a6de-5e36808db3a4",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "d1ce842b-7a72-4d43-8f6b-5c66a2f23d30",
                            "uuid": "921f9336-87ab-438b-8080-ae43bf07195a",
                        },
                        {
                            "destination_uuid": "d1ce842b-7a72-4d43-8f6b-5c66a2f23d30",
                            "uuid": "aa5e3aff-d02d-44bf-a00d-584f338c90f8",
                        },
                    ],
                    "router": {
                        "cases": [
                            {
                                "arguments": ["Success"],
                                "category_uuid": "138ad1f8-318c-470e-933e-e09ea5528e29",
                                "type": "has_only_text",
                                "uuid": "4c6c84c4-419b-4d9d-bc69-49cb06012bad",
                            }
                        ],
                        "categories": [
                            {
                                "exit_uuid": "921f9336-87ab-438b-8080-ae43bf07195a",
                                "name": "Success",
                                "uuid": "138ad1f8-318c-470e-933e-e09ea5528e29",
                            },
                            {
                                "exit_uuid": "aa5e3aff-d02d-44bf-a00d-584f338c90f8",
                                "name": "Failure",
                                "uuid": "d3bb8424-8cbd-45b2-9aea-2d8278ad5701",
                            },
                        ],
                        "default_category_uuid": "d3bb8424-8cbd-45b2-9aea-2d8278ad5701",
                        "operand": "@results.result.category",
                        "type": "switch",
                    },
                    "uuid": "f2b1a441-8a0f-4647-ac35-990a43b44bb2",
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
                            "uuid": "05e9ac09-3222-4f6a-b844-78a2e948edab",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "b4d5b917-bef0-449e-b616-90e3b01a4c3d",
                            "uuid": "d3849552-4f7e-41cf-b863-f2c11b6482bf",
                        },
                        {
                            "destination_uuid": "b4d5b917-bef0-449e-b616-90e3b01a4c3d",
                            "uuid": "7797491e-cf28-4ac7-84f0-13c7b6dd1a64",
                        },
                    ],
                    "router": {
                        "cases": [
                            {
                                "arguments": ["Success"],
                                "category_uuid": "c3f637de-5bb5-4bc4-83eb-e1ac02258e2f",
                                "type": "has_only_text",
                                "uuid": "42475384-931f-43aa-831f-88a9a26e0193",
                            }
                        ],
                        "categories": [
                            {
                                "exit_uuid": "d3849552-4f7e-41cf-b863-f2c11b6482bf",
                                "name": "Success",
                                "uuid": "c3f637de-5bb5-4bc4-83eb-e1ac02258e2f",
                            },
                            {
                                "exit_uuid": "7797491e-cf28-4ac7-84f0-13c7b6dd1a64",
                                "name": "Failure",
                                "uuid": "f9bbf1f1-9411-4657-85b9-dee734259773",
                            },
                        ],
                        "default_category_uuid": "f9bbf1f1-9411-4657-85b9-dee734259773",
                        "operand": "@results.result.category",
                        "type": "switch",
                    },
                    "uuid": "33244906-ad00-43a5-bbcc-1261eb56908f",
                },
                {
                    "actions": [
                        {
                            "attachments": [],
                            "quick_replies": [],
                            "text": "Deixe um coment\u00e1rio sobre sua experi\u00eancia com nosso atendimento \u270d\ufe0f",
                            "type": "send_msg",
                            "uuid": "e4ae4119-afa9-4a67-a347-c35bcd49a083",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "2996a5f5-c514-4aac-8611-d45184f41dff",
                            "uuid": "ac230ab8-4d4a-40b8-9027-5187610fe897",
                        }
                    ],
                    "uuid": "d1ce842b-7a72-4d43-8f6b-5c66a2f23d30",
                },
                {
                    "actions": [],
                    "exits": [
                        {
                            "destination_uuid": "f9375a98-1ce1-4b4e-bc8c-a616ce53d4fe",
                            "uuid": "eb9b8f87-d52f-4821-a484-3b77b9e9f890",
                        },
                        {
                            "destination_uuid": "9ddb6ec6-4415-492d-b7ad-185e1df58f5f",
                            "uuid": "8d9a5ad7-a24f-4897-8883-38c88695b602",
                        },
                    ],
                    "router": {
                        "cases": [],
                        "categories": [
                            {
                                "exit_uuid": "eb9b8f87-d52f-4821-a484-3b77b9e9f890",
                                "name": "All Responses",
                                "uuid": "15be6976-7f8e-429d-99c2-eaf5eabef787",
                            },
                            {
                                "exit_uuid": "8d9a5ad7-a24f-4897-8883-38c88695b602",
                                "name": "No Response",
                                "uuid": "1f5abf33-568f-40e8-b008-0b62acb18fc2",
                            },
                        ],
                        "default_category_uuid": "15be6976-7f8e-429d-99c2-eaf5eabef787",
                        "operand": "@input.text",
                        "result_name": "comentario",
                        "type": "switch",
                        "wait": {
                            "timeout": {
                                "category_uuid": "1f5abf33-568f-40e8-b008-0b62acb18fc2",
                                "seconds": 600,
                            },
                            "type": "msg",
                        },
                    },
                    "uuid": "2996a5f5-c514-4aac-8611-d45184f41dff",
                },
                {
                    "actions": [
                        {
                            "attachments": [],
                            "quick_replies": [],
                            "text": "Deixe um coment\u00e1rio para sempre melhorarmos nosso atendimento \u270d\ufe0f",
                            "type": "send_msg",
                            "uuid": "d6087f51-065f-442b-bf84-53ba2cfe8754",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "89dbc585-8951-4387-b224-478877bfacec",
                            "uuid": "9e1f374f-9967-474a-90d9-76d3ecd3f636",
                        }
                    ],
                    "uuid": "b4d5b917-bef0-449e-b616-90e3b01a4c3d",
                },
                {
                    "actions": [],
                    "exits": [
                        {
                            "destination_uuid": "0fa75334-f5e3-42c7-96c4-8fa90dd49253",
                            "uuid": "74782300-551b-4f9f-b681-d0df7ab35f8f",
                        },
                        {
                            "destination_uuid": "e19f620f-0ba1-4087-aff7-01bd374689f4",
                            "uuid": "7c0d4f96-76b9-42d8-b023-49a9b6a57005",
                        },
                    ],
                    "router": {
                        "cases": [],
                        "categories": [
                            {
                                "exit_uuid": "74782300-551b-4f9f-b681-d0df7ab35f8f",
                                "name": "All Responses",
                                "uuid": "73835a19-ee54-4b4c-9d6a-0166d59df680",
                            },
                            {
                                "exit_uuid": "7c0d4f96-76b9-42d8-b023-49a9b6a57005",
                                "name": "No Response",
                                "uuid": "889537e3-ee3f-4f2a-8450-de6d8c6ee9cd",
                            },
                        ],
                        "default_category_uuid": "73835a19-ee54-4b4c-9d6a-0166d59df680",
                        "operand": "@input.text",
                        "result_name": "comentario",
                        "type": "switch",
                        "wait": {
                            "timeout": {
                                "category_uuid": "889537e3-ee3f-4f2a-8450-de6d8c6ee9cd",
                                "seconds": 600,
                            },
                            "type": "msg",
                        },
                    },
                    "uuid": "89dbc585-8951-4387-b224-478877bfacec",
                },
                {
                    "actions": [
                        {
                            "attachments": [],
                            "quick_replies": [],
                            "text": "Seu atendimento foi finalizado.\n\nAgradecemos a sua colabora\u00e7\u00e3o. At\u00e9 a pr\u00f3xima \ud83d\udc4b",
                            "type": "send_msg",
                            "uuid": "53e6eba4-26a7-4eba-b632-b4f5c532d4ba",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "1d2b9b30-21a8-4228-80fe-c72c2c270f59",
                            "uuid": "191b0182-cae1-4a4f-bd53-c5450293a894",
                        }
                    ],
                    "uuid": "f9375a98-1ce1-4b4e-bc8c-a616ce53d4fe",
                },
                {
                    "actions": [
                        {
                            "category": "N\u00e3o respondente",
                            "name": "comentario",
                            "type": "set_run_result",
                            "uuid": "5f5845ed-b272-4eb2-a548-ea571365b1e9",
                            "value": "N\u00e3o respondente",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "1d2b9b30-21a8-4228-80fe-c72c2c270f59",
                            "uuid": "9239f433-ffc9-482f-bb17-f8589261f603",
                        }
                    ],
                    "uuid": "9ddb6ec6-4415-492d-b7ad-185e1df58f5f",
                },
                {
                    "actions": [
                        {
                            "attachments": [],
                            "quick_replies": [],
                            "text": "Seu atendimento foi finalizado. Iremos analisar seu coment\u00e1rio com responsabilidade. \n\nAgradecemos a sua colabora\u00e7\u00e3o para melhorar o atendimento. At\u00e9 a pr\u00f3xima \ud83d\udc4b",
                            "type": "send_msg",
                            "uuid": "b5592521-3d93-4422-8262-a49c0a02382a",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "1d2b9b30-21a8-4228-80fe-c72c2c270f59",
                            "uuid": "84f9f12a-403f-4704-9b28-ad1aadcb855e",
                        }
                    ],
                    "uuid": "0fa75334-f5e3-42c7-96c4-8fa90dd49253",
                },
                {
                    "actions": [
                        {
                            "category": "N\u00e3o respondente",
                            "name": "comentario",
                            "type": "set_run_result",
                            "uuid": "eb9090ad-e4c5-4198-ac41-60f09619260e",
                            "value": "N\u00e3o respondente",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "1d2b9b30-21a8-4228-80fe-c72c2c270f59",
                            "uuid": "56b4aea2-a5df-43af-ab91-287580b8e3f8",
                        }
                    ],
                    "uuid": "e19f620f-0ba1-4087-aff7-01bd374689f4",
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
                            "uuid": "192f5c18-46b4-45a8-9870-2264f70375e2",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": None,
                            "uuid": "f049a15b-6ffe-4c2a-8b0c-8f6f8b92040b",
                        },
                        {
                            "destination_uuid": None,
                            "uuid": "f2a04751-43c6-403f-b0f7-ebe91e52d963",
                        },
                    ],
                    "router": {
                        "cases": [
                            {
                                "arguments": ["Success"],
                                "category_uuid": "ada71814-e0b9-4357-8981-0054637445fb",
                                "type": "has_only_text",
                                "uuid": "d28c5963-8725-4c91-9ba7-59d323e6f0be",
                            }
                        ],
                        "categories": [
                            {
                                "exit_uuid": "f049a15b-6ffe-4c2a-8b0c-8f6f8b92040b",
                                "name": "Success",
                                "uuid": "ada71814-e0b9-4357-8981-0054637445fb",
                            },
                            {
                                "exit_uuid": "f2a04751-43c6-403f-b0f7-ebe91e52d963",
                                "name": "Failure",
                                "uuid": "e88d43f0-c1ff-4353-864e-010093c9bfd5",
                            },
                        ],
                        "default_category_uuid": "e88d43f0-c1ff-4353-864e-010093c9bfd5",
                        "operand": "@results.result.category",
                        "type": "switch",
                    },
                    "uuid": "1d2b9b30-21a8-4228-80fe-c72c2c270f59",
                },
            ],
            "spec_version": "13.1.0",
            "type": "messaging",
            "uuid": "f343c55d-f43d-41be-9002-f12439d52b25",
            "revision": 40,
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
