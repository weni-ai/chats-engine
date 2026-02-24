# This is a placeholder and will be changed later to the actual flow definition

CSAT_FLOW_VERSION = 4
CSAT_FLOW_NAME = "Weni Chats CSAT Flow"
CSAT_FLOW_DEFINITION_DATA = {
    "version": "13",
    "site": "https://flows.weni.ai",
    "flows": [
        {
            "_ui": {
                "nodes": {
                    "9364bdc9-c4e8-48b1-b402-ee85d3a503bf": {
                        "position": {
                            "left": "1341.074049511356",
                            "top": "1219.275597947668",
                        },
                        "type": "execute_actions",
                    },
                    "aae60481-01f6-427c-a02e-12e9bd41318d": {
                        "config": {"cases": {}},
                        "position": {
                            "left": "1344.7429126871152",
                            "top": "1474.275597947668",
                        },
                        "type": "split_by_scheme",
                    },
                    "f51dd9da-11c4-4445-96df-dd766829a169": {
                        "position": {
                            "left": "1135.002130439344",
                            "top": "1644.0453112453636",
                        },
                        "type": "execute_actions",
                    },
                    "08bc1266-325d-49ca-beac-c85218a4772c": {
                        "position": {
                            "left": "1537.7174976978713",
                            "top": "1645.4129353706592",
                        },
                        "type": "execute_actions",
                    },
                    "aa505479-3566-4c81-bb42-ecf100605c2d": {
                        "position": {
                            "left": "2102.730635385634",
                            "top": "1864.5697418429131",
                        },
                        "type": "execute_actions",
                    },
                    "66836eb1-7d49-492b-ba1e-898507370bb1": {
                        "config": {"cases": {}},
                        "position": {
                            "left": "1157.2408609900526",
                            "top": "2031.653596440618",
                        },
                        "type": "wait_for_response",
                    },
                    "a86c4b71-3c4d-456a-82f9-13af35ce5788": {
                        "position": {
                            "left": "516.5389376101214",
                            "top": "2184.638408866735",
                        },
                        "type": "execute_actions",
                    },
                    "5a8afed0-597f-4b8e-af22-db4a7ea601e2": {
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
                    "97cc136f-e200-49c1-b023-c4e50e8ea5b8": {
                        "position": {"left": 521, "top": 2346},
                        "type": "execute_actions",
                    },
                    "609b22d8-6b36-427f-b7b8-961eb2d28cd1": {
                        "position": {
                            "left": "1243.6657730270365",
                            "top": "2384.993941290002",
                        },
                        "type": "execute_actions",
                    },
                    "512a1808-bbed-48a6-9c0a-a3e10f5f99da": {
                        "config": {},
                        "position": {"left": "530.5389376101214", "top": 2563},
                        "type": "split_by_webhook",
                    },
                    "66da38a2-747f-4c6f-96b1-3164c7e8d50d": {
                        "config": {},
                        "position": {
                            "left": "1248.6657730270365",
                            "top": "2682.993941290002",
                        },
                        "type": "split_by_webhook",
                    },
                    "2e17664d-a99c-415c-875e-126ec37fab2a": {
                        "position": {"left": "531.1525515926652", "top": 2784},
                        "type": "execute_actions",
                    },
                    "00c99bcb-faf9-4f3a-a7e3-789ef3578a8e": {
                        "config": {"cases": {}},
                        "position": {
                            "left": "525.4199459661597",
                            "top": "2963.3440877475277",
                        },
                        "type": "wait_for_response",
                    },
                    "971ec585-250b-439d-9a12-965fd9b65959": {
                        "position": {
                            "left": "1245.9127841724944",
                            "top": "2969.993941290002",
                        },
                        "type": "execute_actions",
                    },
                    "6cd8fd9a-3602-46f6-a453-8c1b90bc5523": {
                        "config": {"cases": {}},
                        "position": {
                            "left": "1262.3460900709856",
                            "top": "3166.571929565236",
                        },
                        "type": "wait_for_response",
                    },
                    "151b93a0-cbce-448a-9d1d-a693c06211ae": {
                        "position": {
                            "left": "476.41994596615973",
                            "top": "3216.3440877475277",
                        },
                        "type": "execute_actions",
                    },
                    "f8b948ee-307b-4c5a-aa1b-739ffbac9d48": {
                        "position": {
                            "left": "796.927464564468",
                            "top": "3224.6395402223325",
                        },
                        "type": "execute_actions",
                    },
                    "1fb8c0db-8576-4ca8-84f7-8040ed18ad01": {
                        "position": {
                            "left": "1215.3460900709856",
                            "top": "3401.4251190743635",
                        },
                        "type": "execute_actions",
                    },
                    "9ff98af3-5fbf-4b42-abce-ee00247ea301": {
                        "position": {
                            "left": "1479.7303603839714",
                            "top": "3403.84381983449",
                        },
                        "type": "execute_actions",
                    },
                    "2fe821be-0e1a-4914-8aca-d7cb3c824b9b": {
                        "config": {},
                        "position": {
                            "left": "908.7015043077097",
                            "top": "3790.3354566551607",
                        },
                        "type": "split_by_webhook",
                    },
                },
                "stickies": {},
            },
            "expire_after_minutes": 10080,
            "integrations": {"classifiers": [], "ticketers": []},
            "language": "base",
            "localization": {
                "eng": {
                    "02909721-af9c-452e-953a-7bf1ad60768d": {
                        "arguments": ["satisfied"]
                    },
                    "17555c26-d2cf-414e-b159-7170ed420b01": {
                        "attachments": [],
                        "text": [
                            "Your session has ended.\n\nThank you for your feedback. See you next time! \ud83d\udc4b"
                        ],
                    },
                    "17e5bd4a-7e18-474d-8644-4eaa689ebdcd": {
                        "description": [""],
                        "title": ["Neutral \ud83d\ude36"],
                    },
                    "1de7ec2b-b26c-4a7e-85e1-fd69e15fe963": {
                        "description": [""],
                        "title": ["Very dissatisfied \ud83d\ude23"],
                    },
                    "255a956f-fec4-4cb4-a646-a5cbc8d544a9": {
                        "description": [""],
                        "title": ["Satisfied \ud83d\ude42"],
                    },
                    "2b8c1e24-c8f9-474c-9dca-85836a0ea9c5": {
                        "text": [
                            "Your opinion is very important to us and takes less than 1 minute. We appreciate it if you can respond."
                        ],
                        "attachments": [],
                    },
                    "3044bb5b-a497-49d5-bb1b-b5f99c7be5e1": {
                        "arguments": ["Satisfied \ud83d\ude42"]
                    },
                    "35d65118-dea8-4aef-bc73-d05ad186709c": {
                        "arguments": ["Dissatisfied \ud83d\ude41"]
                    },
                    "3c827d47-bea3-4c2b-8bb3-0bc4042bfa1b": {
                        "button_text": ["Select here"],
                        "footer": [
                            "It\u2019s very quick, it won\u2019t even take a minute."
                        ],
                        "header_text": ["Customer Satisfaction Survey"],
                        "quick_replies": [],
                        "text": ["*How would you rate my service?* \ud83d\udc47"],
                    },
                    "4326c368-587d-4e94-bca8-aca541d2e7de": {
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
                    "44fd41c8-e6de-43b7-9374-98a86c1d4d08": {
                        "arguments": ["Very satisfied \ud83d\ude03"]
                    },
                    "4cf7af81-cb7e-4730-ad3f-9a5e622a50f3": {"arguments": ["great"]},
                    "6a6db5e5-2f9c-48fa-96e2-776c95e0a118": {
                        "arguments": ["Neutral \ud83d\ude36"]
                    },
                    "6f6ce4d4-9125-44ce-a082-5a851091e2b1": {
                        "arguments": ["terrible horrible"]
                    },
                    "702cbcde-ae0f-41cd-8347-9ac2cb0b9077": {
                        "attachments": [],
                        "text": [
                            "Leave a comment so we can keep improving our service \u270d\ufe0f"
                        ],
                    },
                    "7e6486e7-9eed-4c33-ac83-bf1596c17ad7": {
                        "attachments": [],
                        "text": [
                            "Your session has ended. We will carefully review your feedback.\n\nThank you for helping us improve our service. See you next time! \ud83d\udc4b"
                        ],
                    },
                    "a3cbb298-0fc2-4410-ba73-cd14e6ba4909": {
                        "arguments": ["Very dissatisfied \ud83d\ude23"]
                    },
                    "aabb6c42-a440-4318-b03a-8cd93064f02f": {
                        "arguments": ["neutral normal ok"]
                    },
                    "cc213a14-75b4-40dc-8435-dee2d6d12b7c": {"arguments": ["good"]},
                    "cf63d24e-3afe-406f-96e8-ed08e74107ca": {
                        "attachments": [],
                        "text": [
                            "Leave a comment about your experience with our service \u270d\ufe0f"
                        ],
                    },
                    "d446133b-0764-4012-bf41-8d48e1bb815a": {
                        "description": [""],
                        "title": ["Dissatisfied \ud83d\ude41"],
                    },
                    "e13cbb73-765f-4618-a092-5b99b256811a": {"arguments": ["bad poor"]},
                    "e30679c6-0b81-4d98-92d4-2a33bac91b54": {
                        "description": [""],
                        "title": ["Very satisfied \ud83d\ude03"],
                    },
                    "a7cffc79-804d-4e7d-918d-3d889ba4c963": {
                        "text": ["Before finishing, tell us about your experience!"],
                        "attachments": [],
                    },
                },
                "por": {
                    "17555c26-d2cf-414e-b159-7170ed420b01": {"attachments": []},
                    "17e5bd4a-7e18-474d-8644-4eaa689ebdcd": {
                        "title": ["Neutro \ud83d\ude36"],
                        "description": [""],
                    },
                    "1de7ec2b-b26c-4a7e-85e1-fd69e15fe963": {
                        "title": ["Muito insatisfeito \ud83d\ude23"],
                        "description": [""],
                    },
                    "255a956f-fec4-4cb4-a646-a5cbc8d544a9": {
                        "title": ["Satisfeito \ud83d\ude42"],
                        "description": [""],
                    },
                    "2b8c1e24-c8f9-474c-9dca-85836a0ea9c5": {"attachments": []},
                    "3c827d47-bea3-4c2b-8bb3-0bc4042bfa1b": {"quick_replies": []},
                    "4326c368-587d-4e94-bca8-aca541d2e7de": {"attachments": []},
                    "702cbcde-ae0f-41cd-8347-9ac2cb0b9077": {"attachments": []},
                    "7e6486e7-9eed-4c33-ac83-bf1596c17ad7": {"attachments": []},
                    "cf63d24e-3afe-406f-96e8-ed08e74107ca": {"attachments": []},
                    "d446133b-0764-4012-bf41-8d48e1bb815a": {
                        "title": ["Insatisfeito \ud83d\ude41"],
                        "description": [""],
                    },
                    "e30679c6-0b81-4d98-92d4-2a33bac91b54": {
                        "title": ["Muito satisfeito \ud83d\ude03"],
                        "description": [""],
                    },
                },
                "spa": {
                    "02909721-af9c-452e-953a-7bf1ad60768d": {
                        "arguments": ["satisfecho satisfecha"]
                    },
                    "17555c26-d2cf-414e-b159-7170ed420b01": {
                        "attachments": [],
                        "text": [
                            "Tu atenci\u00f3n ha finalizado.\n\nAgradecemos tu colaboraci\u00f3n. \u00a1Hasta la pr\u00f3xima! \ud83d\udc4b"
                        ],
                    },
                    "17e5bd4a-7e18-474d-8644-4eaa689ebdcd": {
                        "description": [""],
                        "title": ["Neutral \ud83d\ude36"],
                    },
                    "1de7ec2b-b26c-4a7e-85e1-fd69e15fe963": {
                        "description": [""],
                        "title": ["Muy insatisfecho \ud83d\ude23"],
                    },
                    "255a956f-fec4-4cb4-a646-a5cbc8d544a9": {
                        "description": [""],
                        "title": ["Satisfecho \ud83d\ude42"],
                    },
                    "2b8c1e24-c8f9-474c-9dca-85836a0ea9c5": {
                        "text": [
                            "Su opini\u00f3n es muy importante para nosotros y le tomar\u00e1 menos de 1 minuto. Le agradecemos si puede responder."
                        ],
                        "attachments": [],
                    },
                    "3044bb5b-a497-49d5-bb1b-b5f99c7be5e1": {
                        "arguments": ["Satisfecho \ud83d\ude42"]
                    },
                    "35d65118-dea8-4aef-bc73-d05ad186709c": {
                        "arguments": ["Insatisfecho \ud83d\ude41"]
                    },
                    "3c827d47-bea3-4c2b-8bb3-0bc4042bfa1b": {
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
                    "4326c368-587d-4e94-bca8-aca541d2e7de": {
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
                    "44fd41c8-e6de-43b7-9374-98a86c1d4d08": {
                        "arguments": ["Muy satisfecho \ud83d\ude03"]
                    },
                    "4cf7af81-cb7e-4730-ad3f-9a5e622a50f3": {
                        "arguments": ["excelente"]
                    },
                    "6a6db5e5-2f9c-48fa-96e2-776c95e0a118": {
                        "arguments": ["Neutral \ud83d\ude36"]
                    },
                    "6f6ce4d4-9125-44ce-a082-5a851091e2b1": {
                        "arguments": ["horrible terrible"]
                    },
                    "702cbcde-ae0f-41cd-8347-9ac2cb0b9077": {
                        "attachments": [],
                        "text": [
                            "D\u00e9janos un comentario para que podamos seguir mejorando nuestra atenci\u00f3n \u270d\ufe0f"
                        ],
                    },
                    "7e6486e7-9eed-4c33-ac83-bf1596c17ad7": {
                        "attachments": [],
                        "text": [
                            "Tu atenci\u00f3n ha finalizado. Analizaremos tu comentario con responsabilidad.\n\nGracias por ayudarnos a mejorar nuestra atenci\u00f3n. \u00a1Hasta la pr\u00f3xima! \ud83d\udc4b"
                        ],
                    },
                    "a3cbb298-0fc2-4410-ba73-cd14e6ba4909": {
                        "arguments": ["Muy insatisfecho \ud83d\ude23"]
                    },
                    "aabb6c42-a440-4318-b03a-8cd93064f02f": {
                        "arguments": ["normal neutral"]
                    },
                    "cc213a14-75b4-40dc-8435-dee2d6d12b7c": {
                        "arguments": ["bueno buena"]
                    },
                    "cf63d24e-3afe-406f-96e8-ed08e74107ca": {
                        "attachments": [],
                        "text": [
                            "D\u00e9janos un comentario sobre tu experiencia con nuestra atenci\u00f3n \u270d\ufe0f"
                        ],
                    },
                    "d446133b-0764-4012-bf41-8d48e1bb815a": {
                        "description": [""],
                        "title": ["Insatisfecho \ud83d\ude41"],
                    },
                    "e13cbb73-765f-4618-a092-5b99b256811a": {
                        "arguments": ["malo mala"]
                    },
                    "e30679c6-0b81-4d98-92d4-2a33bac91b54": {
                        "description": [""],
                        "title": ["Muy satisfecho \ud83d\ude03"],
                    },
                    "a7cffc79-804d-4e7d-918d-3d889ba4c963": {
                        "text": [
                            "Antes de finalizar, cu\u00e9ntanos c\u00f3mo fue tu experiencia."
                        ],
                        "attachments": [],
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
                            "uuid": "52fe27e4-6dcc-4fc4-8258-79b52168219f",
                            "value": "0",
                        },
                        {
                            "attachments": [],
                            "quick_replies": [],
                            "text": "Antes de encerrar, conte como foi sua experi\u00eancia!",
                            "type": "send_msg",
                            "uuid": "a7cffc79-804d-4e7d-918d-3d889ba4c963",
                        },
                    ],
                    "exits": [
                        {
                            "destination_uuid": "aae60481-01f6-427c-a02e-12e9bd41318d",
                            "uuid": "201aab2a-06c5-4aa8-a09d-f246c37f815c",
                        }
                    ],
                    "uuid": "9364bdc9-c4e8-48b1-b402-ee85d3a503bf",
                },
                {
                    "actions": [],
                    "exits": [
                        {
                            "destination_uuid": "f51dd9da-11c4-4445-96df-dd766829a169",
                            "uuid": "6b080ef8-d33a-444a-843f-b43537552ae6",
                        },
                        {
                            "destination_uuid": "08bc1266-325d-49ca-beac-c85218a4772c",
                            "uuid": "321cd19f-c409-4eff-8bc4-761d90f80d1f",
                        },
                    ],
                    "router": {
                        "cases": [
                            {
                                "arguments": ["whatsapp"],
                                "category_uuid": "363ed097-36da-4435-9d23-63d2c7311aca",
                                "type": "has_only_phrase",
                                "uuid": "2c15a1a2-6fd6-4714-82d7-a635c86fb57e",
                            }
                        ],
                        "categories": [
                            {
                                "exit_uuid": "6b080ef8-d33a-444a-843f-b43537552ae6",
                                "name": "WhatsApp",
                                "uuid": "363ed097-36da-4435-9d23-63d2c7311aca",
                            },
                            {
                                "exit_uuid": "321cd19f-c409-4eff-8bc4-761d90f80d1f",
                                "name": "Other",
                                "uuid": "326b478e-d379-44e8-8347-ea2f90271419",
                            },
                        ],
                        "default_category_uuid": "326b478e-d379-44e8-8347-ea2f90271419",
                        "operand": "@(urn_parts(contact.urn).scheme)",
                        "result_name": "",
                        "type": "switch",
                    },
                    "uuid": "aae60481-01f6-427c-a02e-12e9bd41318d",
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
                                    "uuid": "1de7ec2b-b26c-4a7e-85e1-fd69e15fe963",
                                },
                                {
                                    "description": "",
                                    "title": "Insatisfeito \ud83d\ude41",
                                    "uuid": "d446133b-0764-4012-bf41-8d48e1bb815a",
                                },
                                {
                                    "description": "",
                                    "title": "Neutro \ud83d\ude36",
                                    "uuid": "17e5bd4a-7e18-474d-8644-4eaa689ebdcd",
                                },
                                {
                                    "description": "",
                                    "title": "Satisfeito \ud83d\ude42",
                                    "uuid": "255a956f-fec4-4cb4-a646-a5cbc8d544a9",
                                },
                                {
                                    "description": "",
                                    "title": "Muito satisfeito \ud83d\ude03",
                                    "uuid": "e30679c6-0b81-4d98-92d4-2a33bac91b54",
                                },
                            ],
                            "messageType": "interactive",
                            "quick_replies": [],
                            "text": "*Como voc\u00ea avalia o meu atendimento?* \ud83d\udc47",
                            "type": "send_whatsapp_msg",
                            "uuid": "3c827d47-bea3-4c2b-8bb3-0bc4042bfa1b",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "66836eb1-7d49-492b-ba1e-898507370bb1",
                            "uuid": "660903a9-41e6-4b0a-8759-c65c9490b283",
                        }
                    ],
                    "uuid": "f51dd9da-11c4-4445-96df-dd766829a169",
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
                            "uuid": "4326c368-587d-4e94-bca8-aca541d2e7de",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "66836eb1-7d49-492b-ba1e-898507370bb1",
                            "uuid": "d08926e7-55c7-4053-a7bf-df8a9ef4e386",
                        }
                    ],
                    "uuid": "08bc1266-325d-49ca-beac-c85218a4772c",
                },
                {
                    "actions": [
                        {
                            "attachments": [],
                            "quick_replies": [],
                            "text": "Sua opini\u00e3o \u00e9 muito importante para n\u00f3s e leva menos de 1 minuto. Agradecemos se puder responder.",
                            "type": "send_msg",
                            "uuid": "2b8c1e24-c8f9-474c-9dca-85836a0ea9c5",
                        },
                        {
                            "category": "",
                            "name": "tentativa",
                            "type": "set_run_result",
                            "uuid": "7c0e30ee-2b6c-4d8c-b4e0-a1422a328064",
                            "value": "@(results.tentativa +1)",
                        },
                    ],
                    "exits": [
                        {
                            "destination_uuid": "aae60481-01f6-427c-a02e-12e9bd41318d",
                            "uuid": "f65ef80f-c7dc-46f0-9f86-d9671acc9bf6",
                        }
                    ],
                    "uuid": "aa505479-3566-4c81-bb42-ecf100605c2d",
                },
                {
                    "actions": [],
                    "exits": [
                        {
                            "destination_uuid": "a86c4b71-3c4d-456a-82f9-13af35ce5788",
                            "uuid": "dbb16d3c-1ca4-47ce-ba2c-20790290ceb1",
                        },
                        {
                            "destination_uuid": "a86c4b71-3c4d-456a-82f9-13af35ce5788",
                            "uuid": "2bc235b2-fbe9-4df9-a099-aec50b94236d",
                        },
                        {
                            "destination_uuid": "609b22d8-6b36-427f-b7b8-961eb2d28cd1",
                            "uuid": "e1d7d53f-d946-4403-a53d-b8a4dc967c52",
                        },
                        {
                            "destination_uuid": "609b22d8-6b36-427f-b7b8-961eb2d28cd1",
                            "uuid": "2b03cd00-13d5-4ad4-8e78-3158c3badf91",
                        },
                        {
                            "destination_uuid": "609b22d8-6b36-427f-b7b8-961eb2d28cd1",
                            "uuid": "82496877-6ea0-4d51-9abc-091ca665086e",
                        },
                        {
                            "destination_uuid": "5a8afed0-597f-4b8e-af22-db4a7ea601e2",
                            "uuid": "22a651d9-61d5-4ef4-aa14-7238c993fd1f",
                        },
                        {
                            "destination_uuid": "5a8afed0-597f-4b8e-af22-db4a7ea601e2",
                            "uuid": "9d990e82-6c27-4718-92c5-87b61462a776",
                        },
                    ],
                    "router": {
                        "cases": [
                            {
                                "arguments": ["Muito satisfeito \ud83d\ude03"],
                                "category_uuid": "aaef945d-4414-4d11-ad97-76df2307b878",
                                "type": "has_only_phrase",
                                "uuid": "44fd41c8-e6de-43b7-9374-98a86c1d4d08",
                            },
                            {
                                "arguments": ["Satisfeito \ud83d\ude42"],
                                "category_uuid": "1750e3b0-2ad4-4abd-bd4c-b529e7ba80db",
                                "type": "has_only_phrase",
                                "uuid": "3044bb5b-a497-49d5-bb1b-b5f99c7be5e1",
                            },
                            {
                                "arguments": ["Neutro \ud83d\ude36"],
                                "category_uuid": "4fd5d20d-235f-4121-94c1-1abbb10e4d10",
                                "type": "has_only_phrase",
                                "uuid": "6a6db5e5-2f9c-48fa-96e2-776c95e0a118",
                            },
                            {
                                "arguments": ["Insatisfeito \ud83d\ude41"],
                                "category_uuid": "ab2cdf2a-3b40-41c2-907f-e013f624c259",
                                "type": "has_only_phrase",
                                "uuid": "35d65118-dea8-4aef-bc73-d05ad186709c",
                            },
                            {
                                "arguments": ["Muito insatisfeito \ud83d\ude23"],
                                "category_uuid": "74e6dc6f-b242-40ed-918a-332ed1219d7e",
                                "type": "has_only_phrase",
                                "uuid": "a3cbb298-0fc2-4410-ba73-cd14e6ba4909",
                            },
                            {
                                "arguments": ["\u00f3timo otimo"],
                                "category_uuid": "aaef945d-4414-4d11-ad97-76df2307b878",
                                "type": "has_any_word",
                                "uuid": "4cf7af81-cb7e-4730-ad3f-9a5e622a50f3",
                            },
                            {
                                "arguments": ["bom boa"],
                                "category_uuid": "1750e3b0-2ad4-4abd-bd4c-b529e7ba80db",
                                "type": "has_any_word",
                                "uuid": "cc213a14-75b4-40dc-8435-dee2d6d12b7c",
                            },
                            {
                                "arguments": ["neutro neutra normal"],
                                "category_uuid": "4fd5d20d-235f-4121-94c1-1abbb10e4d10",
                                "type": "has_any_word",
                                "uuid": "aabb6c42-a440-4318-b03a-8cd93064f02f",
                            },
                            {
                                "arguments": ["ruim rum"],
                                "category_uuid": "ab2cdf2a-3b40-41c2-907f-e013f624c259",
                                "type": "has_any_word",
                                "uuid": "e13cbb73-765f-4618-a092-5b99b256811a",
                            },
                            {
                                "arguments": ["p\u00e9ssimo pessimo pesimo"],
                                "category_uuid": "74e6dc6f-b242-40ed-918a-332ed1219d7e",
                                "type": "has_any_word",
                                "uuid": "6f6ce4d4-9125-44ce-a082-5a851091e2b1",
                            },
                            {
                                "arguments": ["satisfeito satisfeita"],
                                "category_uuid": "1750e3b0-2ad4-4abd-bd4c-b529e7ba80db",
                                "type": "has_any_word",
                                "uuid": "02909721-af9c-452e-953a-7bf1ad60768d",
                            },
                        ],
                        "categories": [
                            {
                                "exit_uuid": "dbb16d3c-1ca4-47ce-ba2c-20790290ceb1",
                                "name": "5",
                                "uuid": "aaef945d-4414-4d11-ad97-76df2307b878",
                            },
                            {
                                "exit_uuid": "2bc235b2-fbe9-4df9-a099-aec50b94236d",
                                "name": "4",
                                "uuid": "1750e3b0-2ad4-4abd-bd4c-b529e7ba80db",
                            },
                            {
                                "exit_uuid": "e1d7d53f-d946-4403-a53d-b8a4dc967c52",
                                "name": "3",
                                "uuid": "4fd5d20d-235f-4121-94c1-1abbb10e4d10",
                            },
                            {
                                "exit_uuid": "2b03cd00-13d5-4ad4-8e78-3158c3badf91",
                                "name": "2",
                                "uuid": "ab2cdf2a-3b40-41c2-907f-e013f624c259",
                            },
                            {
                                "exit_uuid": "82496877-6ea0-4d51-9abc-091ca665086e",
                                "name": "1",
                                "uuid": "74e6dc6f-b242-40ed-918a-332ed1219d7e",
                            },
                            {
                                "exit_uuid": "22a651d9-61d5-4ef4-aa14-7238c993fd1f",
                                "name": "Other",
                                "uuid": "c4bb359d-29ba-4d43-a405-c8ef0d281883",
                            },
                            {
                                "exit_uuid": "9d990e82-6c27-4718-92c5-87b61462a776",
                                "name": "No Response",
                                "uuid": "1d0da640-8a82-4889-ae96-f35ddd2f755a",
                            },
                        ],
                        "default_category_uuid": "c4bb359d-29ba-4d43-a405-c8ef0d281883",
                        "operand": "@input.text",
                        "result_name": "avaliacao",
                        "type": "switch",
                        "wait": {
                            "timeout": {
                                "category_uuid": "1d0da640-8a82-4889-ae96-f35ddd2f755a",
                                "seconds": 600,
                            },
                            "type": "msg",
                        },
                    },
                    "uuid": "66836eb1-7d49-492b-ba1e-898507370bb1",
                },
                {
                    "actions": [
                        {
                            "field": {
                                "key": "nota_pesquisa_atendimento_humano",
                                "name": "Nota Pesquisa Atendimento Humano",
                            },
                            "type": "set_contact_field",
                            "uuid": "0f8f5176-40ac-4a72-a8c4-9c727902d6d8",
                            "value": "@results.avaliacao.category",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "97cc136f-e200-49c1-b023-c4e50e8ea5b8",
                            "uuid": "a4df67c9-b8b2-4143-ab9c-4209eb538b9e",
                        }
                    ],
                    "uuid": "a86c4b71-3c4d-456a-82f9-13af35ce5788",
                },
                {
                    "actions": [],
                    "exits": [
                        {
                            "destination_uuid": None,
                            "uuid": "429a2dd2-5b53-450a-9093-2d0ea8dcc6a6",
                        },
                        {
                            "destination_uuid": "aa505479-3566-4c81-bb42-ecf100605c2d",
                            "uuid": "176b1baf-76a3-4d30-851f-b71c7f167d5c",
                        },
                    ],
                    "router": {
                        "cases": [
                            {
                                "arguments": ["1"],
                                "category_uuid": "073149d2-ea52-47a0-a813-e3a2a1456944",
                                "type": "has_any_word",
                                "uuid": "1c009ece-c516-4c4c-a33a-de2b68337262",
                            }
                        ],
                        "categories": [
                            {
                                "exit_uuid": "429a2dd2-5b53-450a-9093-2d0ea8dcc6a6",
                                "name": "J\u00e1 tentou 1x",
                                "uuid": "073149d2-ea52-47a0-a813-e3a2a1456944",
                            },
                            {
                                "exit_uuid": "176b1baf-76a3-4d30-851f-b71c7f167d5c",
                                "name": "Other",
                                "uuid": "082a7cb4-d0e6-41ab-854f-98e87ac9b854",
                            },
                        ],
                        "default_category_uuid": "082a7cb4-d0e6-41ab-854f-98e87ac9b854",
                        "operand": "@results.tentativa",
                        "type": "switch",
                    },
                    "uuid": "5a8afed0-597f-4b8e-af22-db4a7ea601e2",
                },
                {
                    "actions": [
                        {
                            "category": "@results.avaliacao.category",
                            "name": "avaliacao",
                            "type": "set_run_result",
                            "uuid": "729245e5-1297-4913-bc16-d57bc4667bd7",
                            "value": "@results.avaliacao.category",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "512a1808-bbed-48a6-9c0a-a3e10f5f99da",
                            "uuid": "de1c3126-79ab-4754-ab2f-0a161b42209d",
                        }
                    ],
                    "uuid": "97cc136f-e200-49c1-b023-c4e50e8ea5b8",
                },
                {
                    "actions": [
                        {
                            "field": {
                                "key": "nota_pesquisa_atendimento_humano",
                                "name": "Nota Pesquisa Atendimento Humano",
                            },
                            "type": "set_contact_field",
                            "uuid": "3d0df8d7-1f93-4230-abee-5ddb6b68997d",
                            "value": "@results.avaliacao.category",
                        },
                        {
                            "category": "@results.avaliacao.category",
                            "name": "avaliacao",
                            "type": "set_run_result",
                            "uuid": "1226e58a-97d7-4810-8cc6-d3fdb255fe7a",
                            "value": "@results.avaliacao.category",
                        },
                    ],
                    "exits": [
                        {
                            "destination_uuid": "66da38a2-747f-4c6f-96b1-3164c7e8d50d",
                            "uuid": "827f6bbf-829d-4433-820f-d1150f57dbc5",
                        }
                    ],
                    "uuid": "609b22d8-6b36-427f-b7b8-961eb2d28cd1",
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
                            "uuid": "3012ffae-75bb-4396-b70d-05412b55c72d",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "2e17664d-a99c-415c-875e-126ec37fab2a",
                            "uuid": "c7bb1898-a3d0-4dfa-aed6-5c74dc2ce6a6",
                        },
                        {
                            "destination_uuid": "2e17664d-a99c-415c-875e-126ec37fab2a",
                            "uuid": "37f061bd-b5d4-4378-8e5d-d6d705b65f38",
                        },
                    ],
                    "router": {
                        "cases": [
                            {
                                "arguments": ["Success"],
                                "category_uuid": "83b01a61-2dcb-4856-9fe9-88f464158126",
                                "type": "has_only_text",
                                "uuid": "6ed5f61b-8ff3-4806-8d99-3ba1e9c45b29",
                            }
                        ],
                        "categories": [
                            {
                                "exit_uuid": "c7bb1898-a3d0-4dfa-aed6-5c74dc2ce6a6",
                                "name": "Success",
                                "uuid": "83b01a61-2dcb-4856-9fe9-88f464158126",
                            },
                            {
                                "exit_uuid": "37f061bd-b5d4-4378-8e5d-d6d705b65f38",
                                "name": "Failure",
                                "uuid": "5ac26187-df59-4ae2-85eb-5a226575a783",
                            },
                        ],
                        "default_category_uuid": "5ac26187-df59-4ae2-85eb-5a226575a783",
                        "operand": "@results.result.category",
                        "type": "switch",
                    },
                    "uuid": "512a1808-bbed-48a6-9c0a-a3e10f5f99da",
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
                            "uuid": "35a97076-39a2-4930-8a1a-760a9023293d",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "971ec585-250b-439d-9a12-965fd9b65959",
                            "uuid": "304aecc9-4035-49cb-a432-4a8c85bdc98d",
                        },
                        {
                            "destination_uuid": "971ec585-250b-439d-9a12-965fd9b65959",
                            "uuid": "bf83e842-f70b-40cb-8e1d-38adda1e2c82",
                        },
                    ],
                    "router": {
                        "cases": [
                            {
                                "arguments": ["Success"],
                                "category_uuid": "5ada9691-2e74-4a2e-bf48-e3858fdac201",
                                "type": "has_only_text",
                                "uuid": "6fe4bd29-06df-48d2-9244-778755337dc0",
                            }
                        ],
                        "categories": [
                            {
                                "exit_uuid": "304aecc9-4035-49cb-a432-4a8c85bdc98d",
                                "name": "Success",
                                "uuid": "5ada9691-2e74-4a2e-bf48-e3858fdac201",
                            },
                            {
                                "exit_uuid": "bf83e842-f70b-40cb-8e1d-38adda1e2c82",
                                "name": "Failure",
                                "uuid": "2ee51c8e-5817-4103-baf3-8335f88bf67a",
                            },
                        ],
                        "default_category_uuid": "2ee51c8e-5817-4103-baf3-8335f88bf67a",
                        "operand": "@results.result.category",
                        "type": "switch",
                    },
                    "uuid": "66da38a2-747f-4c6f-96b1-3164c7e8d50d",
                },
                {
                    "actions": [
                        {
                            "attachments": [],
                            "quick_replies": [],
                            "text": "Deixe um coment\u00e1rio sobre sua experi\u00eancia com nosso atendimento \u270d\ufe0f",
                            "type": "send_msg",
                            "uuid": "cf63d24e-3afe-406f-96e8-ed08e74107ca",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "00c99bcb-faf9-4f3a-a7e3-789ef3578a8e",
                            "uuid": "7d506cd1-4dda-487e-8405-193460f98bbf",
                        }
                    ],
                    "uuid": "2e17664d-a99c-415c-875e-126ec37fab2a",
                },
                {
                    "actions": [],
                    "exits": [
                        {
                            "destination_uuid": "151b93a0-cbce-448a-9d1d-a693c06211ae",
                            "uuid": "6f69b94d-711b-48f5-9471-9cfb5a82018a",
                        },
                        {
                            "destination_uuid": "f8b948ee-307b-4c5a-aa1b-739ffbac9d48",
                            "uuid": "b5f09d53-959e-4db8-856b-4ea6d8b6e4e0",
                        },
                    ],
                    "router": {
                        "cases": [],
                        "categories": [
                            {
                                "exit_uuid": "6f69b94d-711b-48f5-9471-9cfb5a82018a",
                                "name": "All Responses",
                                "uuid": "3fb7f3f9-ced5-4001-8b1b-b7155ef6a2c6",
                            },
                            {
                                "exit_uuid": "b5f09d53-959e-4db8-856b-4ea6d8b6e4e0",
                                "name": "No Response",
                                "uuid": "39506f02-b492-4211-8aa1-5d7a2245a74a",
                            },
                        ],
                        "default_category_uuid": "3fb7f3f9-ced5-4001-8b1b-b7155ef6a2c6",
                        "operand": "@input.text",
                        "result_name": "comentario",
                        "type": "switch",
                        "wait": {
                            "timeout": {
                                "category_uuid": "39506f02-b492-4211-8aa1-5d7a2245a74a",
                                "seconds": 600,
                            },
                            "type": "msg",
                        },
                    },
                    "uuid": "00c99bcb-faf9-4f3a-a7e3-789ef3578a8e",
                },
                {
                    "actions": [
                        {
                            "attachments": [],
                            "quick_replies": [],
                            "text": "Deixe um coment\u00e1rio para sempre melhorarmos nosso atendimento \u270d\ufe0f",
                            "type": "send_msg",
                            "uuid": "702cbcde-ae0f-41cd-8347-9ac2cb0b9077",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "6cd8fd9a-3602-46f6-a453-8c1b90bc5523",
                            "uuid": "0e03c3cb-3e18-487f-9a95-a2412cbafb10",
                        }
                    ],
                    "uuid": "971ec585-250b-439d-9a12-965fd9b65959",
                },
                {
                    "actions": [],
                    "exits": [
                        {
                            "destination_uuid": "1fb8c0db-8576-4ca8-84f7-8040ed18ad01",
                            "uuid": "e9f859ce-72b8-49ee-b4e1-9b58da9b3e60",
                        },
                        {
                            "destination_uuid": "9ff98af3-5fbf-4b42-abce-ee00247ea301",
                            "uuid": "4f65c0a0-8d78-483b-9079-0542651b5913",
                        },
                    ],
                    "router": {
                        "cases": [],
                        "categories": [
                            {
                                "exit_uuid": "e9f859ce-72b8-49ee-b4e1-9b58da9b3e60",
                                "name": "All Responses",
                                "uuid": "688ec254-b83d-4c97-b545-a8df002b8e40",
                            },
                            {
                                "exit_uuid": "4f65c0a0-8d78-483b-9079-0542651b5913",
                                "name": "No Response",
                                "uuid": "355e0346-e9bc-4cb7-accb-407e1377c554",
                            },
                        ],
                        "default_category_uuid": "688ec254-b83d-4c97-b545-a8df002b8e40",
                        "operand": "@input.text",
                        "result_name": "comentario",
                        "type": "switch",
                        "wait": {
                            "timeout": {
                                "category_uuid": "355e0346-e9bc-4cb7-accb-407e1377c554",
                                "seconds": 600,
                            },
                            "type": "msg",
                        },
                    },
                    "uuid": "6cd8fd9a-3602-46f6-a453-8c1b90bc5523",
                },
                {
                    "actions": [
                        {
                            "attachments": [],
                            "quick_replies": [],
                            "text": "Seu atendimento foi finalizado.\n\nAgradecemos a sua colabora\u00e7\u00e3o. At\u00e9 a pr\u00f3xima \ud83d\udc4b",
                            "type": "send_msg",
                            "uuid": "17555c26-d2cf-414e-b159-7170ed420b01",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "2fe821be-0e1a-4914-8aca-d7cb3c824b9b",
                            "uuid": "622c84d4-006f-4e78-81f6-acbb3c49c955",
                        }
                    ],
                    "uuid": "151b93a0-cbce-448a-9d1d-a693c06211ae",
                },
                {
                    "actions": [
                        {
                            "category": "N\u00e3o respondente",
                            "name": "comentario",
                            "type": "set_run_result",
                            "uuid": "59d75084-5509-4c7d-b933-fe9839729487",
                            "value": "N\u00e3o respondente",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "2fe821be-0e1a-4914-8aca-d7cb3c824b9b",
                            "uuid": "46652981-98ee-43c9-b0e4-a047319f81d6",
                        }
                    ],
                    "uuid": "f8b948ee-307b-4c5a-aa1b-739ffbac9d48",
                },
                {
                    "actions": [
                        {
                            "attachments": [],
                            "quick_replies": [],
                            "text": "Seu atendimento foi finalizado. Iremos analisar seu coment\u00e1rio com responsabilidade. \n\nAgradecemos a sua colabora\u00e7\u00e3o para melhorar o atendimento. At\u00e9 a pr\u00f3xima \ud83d\udc4b",
                            "type": "send_msg",
                            "uuid": "7e6486e7-9eed-4c33-ac83-bf1596c17ad7",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "2fe821be-0e1a-4914-8aca-d7cb3c824b9b",
                            "uuid": "2c8ef375-8c7d-4a55-bca4-e623a4a042ea",
                        }
                    ],
                    "uuid": "1fb8c0db-8576-4ca8-84f7-8040ed18ad01",
                },
                {
                    "actions": [
                        {
                            "category": "N\u00e3o respondente",
                            "name": "comentario",
                            "type": "set_run_result",
                            "uuid": "18530355-0ce4-4855-8296-f01a14adf40e",
                            "value": "N\u00e3o respondente",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "2fe821be-0e1a-4914-8aca-d7cb3c824b9b",
                            "uuid": "d075dccb-7dcd-4516-b876-d0e54ca5c743",
                        }
                    ],
                    "uuid": "9ff98af3-5fbf-4b42-abce-ee00247ea301",
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
                            "uuid": "9f80f189-d57a-40ce-a8eb-f1adfee69403",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": None,
                            "uuid": "88d402ab-05cb-4803-ae29-c5c9f14950af",
                        },
                        {
                            "destination_uuid": None,
                            "uuid": "7bf214d7-e633-46f0-9695-608c8a2e7e2a",
                        },
                    ],
                    "router": {
                        "cases": [
                            {
                                "arguments": ["Success"],
                                "category_uuid": "03a7048a-3191-4d46-a8d5-1e97ae4ce453",
                                "type": "has_only_text",
                                "uuid": "2160229b-2c45-477f-9ee2-ac5fb7c0a011",
                            }
                        ],
                        "categories": [
                            {
                                "exit_uuid": "88d402ab-05cb-4803-ae29-c5c9f14950af",
                                "name": "Success",
                                "uuid": "03a7048a-3191-4d46-a8d5-1e97ae4ce453",
                            },
                            {
                                "exit_uuid": "7bf214d7-e633-46f0-9695-608c8a2e7e2a",
                                "name": "Failure",
                                "uuid": "73cc3383-005f-4ffd-9ce5-356cc48e0a46",
                            },
                        ],
                        "default_category_uuid": "73cc3383-005f-4ffd-9ce5-356cc48e0a46",
                        "operand": "@results.result.category",
                        "type": "switch",
                    },
                    "uuid": "2fe821be-0e1a-4914-8aca-d7cb3c824b9b",
                },
            ],
            "spec_version": "13.1.0",
            "type": "messaging",
            "uuid": "f343c55d-f43d-41be-9002-f12439d52b25",
            "revision": 52,
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
