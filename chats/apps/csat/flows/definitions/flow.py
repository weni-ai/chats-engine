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
                    "6c056ac2-b770-46f9-a7c9-d44d92aa2f14": {
                        "position": {
                            "left": "1342.074049511356",
                            "top": "1254.275597947668",
                        },
                        "type": "execute_actions",
                    },
                    "e715d7fb-28bf-425e-be3b-3b45c1bb0af0": {
                        "config": {"cases": {}},
                        "position": {
                            "left": "1344.7429126871152",
                            "top": "1454.653596440618",
                        },
                        "type": "split_by_scheme",
                    },
                    "2857c7ea-5e79-4b13-a73a-cfbe61ae1f6c": {
                        "position": {
                            "left": "1135.002130439344",
                            "top": "1644.0453112453636",
                        },
                        "type": "execute_actions",
                    },
                    "5dedc9fb-c576-46dc-8154-b9ee4850c9dd": {
                        "position": {
                            "left": "1537.7174976978713",
                            "top": "1645.4129353706592",
                        },
                        "type": "execute_actions",
                    },
                    "d5daf3ec-e348-481b-b0e5-2409f90b726d": {
                        "position": {
                            "left": "2102.730635385634",
                            "top": "1864.5697418429131",
                        },
                        "type": "execute_actions",
                    },
                    "4dcffaa1-0674-4363-941b-4f5e3fb0a5b5": {
                        "config": {"cases": {}},
                        "position": {
                            "left": "1157.2408609900526",
                            "top": "2031.653596440618",
                        },
                        "type": "wait_for_response",
                    },
                    "1400533b-0bd5-4466-90e1-d10828454833": {
                        "config": {
                            "cases": {},
                            "operand": {
                                "id": "tentativa",
                                "name": "tentativa",
                                "type": "result",
                            },
                        },
                        "position": {
                            "left": "2222.1872341053704",
                            "top": "2265.7396842221206",
                        },
                        "type": "split_by_run_result",
                    },
                    "c9aa9cda-5e84-4ddf-88d1-4ac4039dd398": {
                        "position": {
                            "left": "516.5389376101214",
                            "top": "2184.638408866735",
                        },
                        "type": "execute_actions",
                    },
                    "4c7a6ce2-a47c-4a93-843c-65713a3d4ada": {
                        "position": {
                            "left": "1211.8007743109872",
                            "top": "2354.7407051418536",
                        },
                        "type": "execute_actions",
                    },
                    "ba65e658-7022-4862-94e6-e79406d5b578": {
                        "position": {"left": "531.1525515926652", "top": 2784},
                        "type": "execute_actions",
                    },
                    "85d9c83e-ed42-4a1b-aab8-f0f2b2673dc6": {
                        "position": {
                            "left": "1212.9127841724944",
                            "top": "2744.0731410222365",
                        },
                        "type": "execute_actions",
                    },
                    "49277b01-5c08-4cf3-b8d9-c979f5ca3eb3": {
                        "position": {
                            "left": "1216.6290399328577",
                            "top": "2946.571929565236",
                        },
                        "type": "execute_actions",
                    },
                    "cb4e32e4-541e-4de6-b0f9-8ba3d433c870": {
                        "config": {"cases": {}},
                        "position": {
                            "left": "525.4199459661597",
                            "top": "2963.3440877475277",
                        },
                        "type": "wait_for_response",
                    },
                    "089c1a3f-be4a-46bd-8979-2d20a81e2580": {
                        "config": {"cases": {}},
                        "position": {
                            "left": "1211.3460900709856",
                            "top": "3197.571929565236",
                        },
                        "type": "wait_for_response",
                    },
                    "e943d3ed-141f-4bb4-abde-83c19e250a05": {
                        "position": {
                            "left": "476.41994596615973",
                            "top": "3216.3440877475277",
                        },
                        "type": "execute_actions",
                    },
                    "fb652fab-817c-42b3-b0f6-19d86d80ee2d": {
                        "position": {
                            "left": "796.927464564468",
                            "top": "3224.6395402223325",
                        },
                        "type": "execute_actions",
                    },
                    "64cf9379-df72-4bf1-b48d-0f1729c119dc": {
                        "position": {
                            "left": "1215.3460900709856",
                            "top": "3401.4251190743635",
                        },
                        "type": "execute_actions",
                    },
                    "9c829e36-8fa3-44f5-bafc-c14bddb8f653": {
                        "position": {
                            "left": "1479.7303603839714",
                            "top": "3403.84381983449",
                        },
                        "type": "execute_actions",
                    },
                    "f9066628-7ec1-465e-bdfe-d9dd90838926": {
                        "config": {},
                        "position": {
                            "left": "908.7015043077097",
                            "top": "3790.3354566551607",
                        },
                        "type": "split_by_webhook",
                    },
                    "1b72166c-2840-4d07-948c-f8978f428f3a": {
                        "type": "split_by_webhook",
                        "position": {"left": "530.5389376101214", "top": 2563},
                        "config": {},
                    },
                    "e2cfc927-abf9-4181-9c59-e09cf969c1bf": {
                        "position": {"left": 521, "top": 2346},
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
                    "07507934-562f-4588-9634-58f7abaa7f31": {
                        "description": [""],
                        "title": ["Very dissatisfied \ud83d\ude23"],
                    },
                    "0ea27bdb-c90c-434e-ba98-4de165e3fa3b": {
                        "description": [""],
                        "title": ["Satisfied \ud83d\ude42"],
                    },
                    "1040779e-c097-4b55-9436-d5d8dc22f550": {
                        "arguments": ["Neutral \ud83d\ude36"]
                    },
                    "143ff141-0735-42d2-865d-d9a77cb5c080": {
                        "arguments": ["terrible horrible"]
                    },
                    "364ccca7-a19c-4fff-bcab-34a7f24c1a14": {
                        "attachments": [],
                        "text": [
                            "Your opinion is very important to us and takes less than 1 minute. We would appreciate it if you could respond."
                        ],
                    },
                    "d47105ad-6376-4aa1-894b-8209de614756": {
                        "attachments": [],
                        "quick_replies": [],
                        "text": [
                            "Before we go, tell us about your experience!"
                        ],
                    },
                    "370acbd7-7295-4e47-b044-8310f989103d": {
                        "arguments": ["Very satisfied \ud83d\ude03"]
                    },
                    "4b92d027-8fd7-4c1a-b911-a953e6cf6850": {"arguments": ["great"]},
                    "560eed3b-c2b3-407a-ba70-5ec7b9e76536": {
                        "arguments": ["Dissatisfied \ud83d\ude41"]
                    },
                    "614b6ee5-97f9-4cf2-a92c-4ef12b2d2400": {"arguments": ["good"]},
                    "6a700f2d-3988-4e5f-8a2f-19149693dc1f": {
                        "attachments": [],
                        "text": [
                            "Leave a comment about your experience with our service \u270d\ufe0f"
                        ],
                    },
                    "781450c5-e6f4-4dde-a03b-51662cbd00ef": {
                        "button_text": ["Select here"],
                        "footer": [
                            "It\u2019s very quick, it won\u2019t even take a minute."
                        ],
                        "header_text": ["Customer Satisfaction Survey"],
                        "quick_replies": [],
                        "text": [
                            "*How would you rate my service?* \ud83d\udc47"
                        ],
                    },
                    "79baa84f-db8c-45a3-bab7-faf791fb1bc4": {
                        "arguments": ["satisfied"]
                    },
                    "7ad88331-4e97-4e1e-b27c-4919210624b3": {
                        "arguments": ["Very dissatisfied \ud83d\ude23"]
                    },
                    "87033018-daf3-45ff-a85e-92f184491528": {
                        "attachments": [],
                        "text": [
                            "Your session has ended. We will carefully review your feedback.\n\nThank you for helping us improve our service. See you next time! \ud83d\udc4b"
                        ],
                    },
                    "89cd9f22-0e86-4ebc-97e3-3e91f7f7760e": {"arguments": ["bad poor"]},
                    "a047bf70-707f-4ddb-9009-a1bc1665d980": {
                        "description": [""],
                        "title": ["Dissatisfied \ud83d\ude41"],
                    },
                    "aa9eb133-f259-41f2-83a2-74c927d7d297": {
                        "attachments": [],
                        "quick_replies": [
                            "Very dissatisfied \ud83d\ude23",
                            "Dissatisfied \ud83d\ude41",
                            "Neutral \ud83d\ude36",
                            "Satisfied \ud83d\ude42",
                            "Very satisfied \ud83d\ude03",
                        ],
                        "text": [
                            "**How would you rate my service?** \ud83d\udc47"
                        ],
                    },
                    "ba177798-f428-441e-b896-0f5670ad97ee": {
                        "attachments": [],
                        "text": [
                            "Leave a comment so we can keep improving our service \u270d\ufe0f"
                        ],
                    },
                    "c8960771-af8e-47c4-9542-5df86ca9edcc": {
                        "description": [""],
                        "title": ["Very satisfied \ud83d\ude03"],
                    },
                    "d3dbf5c4-6404-47b8-a0a8-c739266e82f4": {
                        "attachments": [],
                        "text": [
                            "Your session has ended.\n\nThank you for your feedback. See you next time! \ud83d\udc4b"
                        ],
                    },
                    "d965f29a-55fe-468c-8b9f-7c592d08258d": {
                        "arguments": ["Satisfied \ud83d\ude42"]
                    },
                    "dfb8c7c0-3393-4bc4-b82a-370404af6cdd": {
                        "arguments": ["neutral normal ok"]
                    },
                    "f26e6521-8b6f-43da-a5da-87c1e2529f96": {
                        "description": [""],
                        "title": ["Neutral \ud83d\ude36"],
                    },
                },
                "por": {
                    "07507934-562f-4588-9634-58f7abaa7f31": {
                        "description": [""],
                        "title": ["Muito insatisfeito \ud83d\ude23"],
                    },
                    "0ea27bdb-c90c-434e-ba98-4de165e3fa3b": {
                        "description": [""],
                        "title": ["Satisfeito \ud83d\ude42"],
                    },
                    "364ccca7-a19c-4fff-bcab-34a7f24c1a14": {
                        "attachments": [],
                        "text": [
                            "Sua opinião é muito importante para nós e leva menos de 1 minuto. Agradecemos se puder responder."
                        ],
                    },
                    "d47105ad-6376-4aa1-894b-8209de614756": {
                        "attachments": [],
                        "quick_replies": [],
                        "text": [
                            "Antes de encerrar, conte como foi sua experiência!"
                        ],
                    },
                    "6a700f2d-3988-4e5f-8a2f-19149693dc1f": {
                        "attachments": [],
                        "text": [
                            "Deixe um coment\u00e1rio sobre sua experi\u00eancia com nosso atendimento \u270d\ufe0f"
                        ],
                    },
                    "781450c5-e6f4-4dde-a03b-51662cbd00ef": {
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
                    "87033018-daf3-45ff-a85e-92f184491528": {
                        "attachments": [],
                        "text": [
                            "Seu atendimento foi finalizado. Iremos analisar seu coment\u00e1rio com responsabilidade.\n\nAgradecemos a sua colabora\u00e7\u00e3o para melhorar o atendimento. At\u00e9 a pr\u00f3xima \ud83d\udc4b"
                        ],
                    },
                    "a047bf70-707f-4ddb-9009-a1bc1665d980": {
                        "description": [""],
                        "title": ["Insatisfeito \ud83d\ude41"],
                    },
                    "aa9eb133-f259-41f2-83a2-74c927d7d297": {
                        "attachments": [],
                        "text": [
                            "**Como voc\u00ea avalia o meu atendimento?** \ud83d\udc47"
                        ],
                    },
                    "ba177798-f428-441e-b896-0f5670ad97ee": {
                        "attachments": [],
                        "text": [
                            "Deixe um coment\u00e1rio para sempre melhorarmos nosso atendimento \u270d\ufe0f"
                        ],
                    },
                    "c8960771-af8e-47c4-9542-5df86ca9edcc": {
                        "description": [""],
                        "title": ["Muito satisfeito \ud83d\ude03"],
                    },
                    "d3dbf5c4-6404-47b8-a0a8-c739266e82f4": {
                        "attachments": [],
                        "text": [
                            "Seu atendimento foi finalizado.\n\nAgradecemos a sua colabora\u00e7\u00e3o. At\u00e9 a pr\u00f3xima \ud83d\udc4b"
                        ],
                    },
                    "f26e6521-8b6f-43da-a5da-87c1e2529f96": {
                        "description": [""],
                        "title": ["Neutro \ud83d\ude36"],
                    },
                },
                "spa": {
                    "07507934-562f-4588-9634-58f7abaa7f31": {
                        "description": [""],
                        "title": ["Muy insatisfecho \ud83d\ude23"],
                    },
                    "0ea27bdb-c90c-434e-ba98-4de165e3fa3b": {
                        "description": [""],
                        "title": ["Satisfecho \ud83d\ude42"],
                    },
                    "1040779e-c097-4b55-9436-d5d8dc22f550": {
                        "arguments": ["Neutral \ud83d\ude36"]
                    },
                    "143ff141-0735-42d2-865d-d9a77cb5c080": {
                        "arguments": ["horrible terrible"]
                    },
                    "364ccca7-a19c-4fff-bcab-34a7f24c1a14": {
                        "attachments": [],
                        "text": [
                            "Tu opinión es muy importante para nosotros y toma menos de 1 minuto. Te agradeceríamos si pudieras responder."
                        ],
                    },
                    "d47105ad-6376-4aa1-894b-8209de614756": {
                        "attachments": [],
                        "quick_replies": [],
                        "text": [
                            "Antes de terminar, ¡cuéntanos tu experiencia!"
                        ],
                    },
                    "370acbd7-7295-4e47-b044-8310f989103d": {
                        "arguments": ["Muy satisfecho \ud83d\ude03"]
                    },
                    "4b92d027-8fd7-4c1a-b911-a953e6cf6850": {
                        "arguments": ["excelente"]
                    },
                    "560eed3b-c2b3-407a-ba70-5ec7b9e76536": {
                        "arguments": ["Insatisfecho \ud83d\ude41"]
                    },
                    "614b6ee5-97f9-4cf2-a92c-4ef12b2d2400": {
                        "arguments": ["bueno buena"]
                    },
                    "6a700f2d-3988-4e5f-8a2f-19149693dc1f": {
                        "attachments": [],
                        "text": [
                            "D\u00e9janos un comentario sobre tu experiencia con nuestra atenci\u00f3n \u270d\ufe0f"
                        ],
                    },
                    "781450c5-e6f4-4dde-a03b-51662cbd00ef": {
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
                    "79baa84f-db8c-45a3-bab7-faf791fb1bc4": {
                        "arguments": ["satisfecho satisfecha"]
                    },
                    "7ad88331-4e97-4e1e-b27c-4919210624b3": {
                        "arguments": ["Muy insatisfecho \ud83d\ude23"]
                    },
                    "87033018-daf3-45ff-a85e-92f184491528": {
                        "attachments": [],
                        "text": [
                            "Tu atenci\u00f3n ha finalizado. Analizaremos tu comentario con responsabilidad.\n\nGracias por ayudarnos a mejorar nuestra atenci\u00f3n. \u00a1Hasta la pr\u00f3xima! \ud83d\udc4b"
                        ],
                    },
                    "89cd9f22-0e86-4ebc-97e3-3e91f7f7760e": {
                        "arguments": ["malo mala"]
                    },
                    "a047bf70-707f-4ddb-9009-a1bc1665d980": {
                        "description": [""],
                        "title": ["Insatisfecho \ud83d\ude41"],
                    },
                    "aa9eb133-f259-41f2-83a2-74c927d7d297": {
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
                    "ba177798-f428-441e-b896-0f5670ad97ee": {
                        "attachments": [],
                        "text": [
                            "D\u00e9janos un comentario para que podamos seguir mejorando nuestra atenci\u00f3n \u270d\ufe0f"
                        ],
                    },
                    "c8960771-af8e-47c4-9542-5df86ca9edcc": {
                        "description": [""],
                        "title": ["Muy satisfecho \ud83d\ude03"],
                    },
                    "d3dbf5c4-6404-47b8-a0a8-c739266e82f4": {
                        "attachments": [],
                        "text": [
                            "Tu atenci\u00f3n ha finalizado.\n\nAgradecemos tu colaboraci\u00f3n. \u00a1Hasta la pr\u00f3xima! \ud83d\udc4b"
                        ],
                    },
                    "d965f29a-55fe-468c-8b9f-7c592d08258d": {
                        "arguments": ["Satisfecho \ud83d\ude42"]
                    },
                    "dfb8c7c0-3393-4bc4-b82a-370404af6cdd": {
                        "arguments": ["normal neutral"]
                    },
                    "f26e6521-8b6f-43da-a5da-87c1e2529f96": {
                        "description": [""],
                        "title": ["Neutral \ud83d\ude36"],
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
                            "uuid": "32e842e7-d4c1-4a8b-a558-cffc622687a9",
                            "value": "0",
                        },
                        {
                            "attachments": [],
                            "text": "Antes de encerrar, conte como foi sua experiência!",
                            "type": "send_msg",
                            "quick_replies": [],
                            "uuid": "d47105ad-6376-4aa1-894b-8209de614756",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "e715d7fb-28bf-425e-be3b-3b45c1bb0af0",
                            "uuid": "3f202d08-d8c8-4481-92ff-7e5b7168e619",
                        }
                    ],
                    "uuid": "6c056ac2-b770-46f9-a7c9-d44d92aa2f14",
                },
                {
                    "actions": [],
                    "exits": [
                        {
                            "destination_uuid": "2857c7ea-5e79-4b13-a73a-cfbe61ae1f6c",
                            "uuid": "4960c299-51c4-4f2a-addb-efa9f01da6d8",
                        },
                        {
                            "destination_uuid": "5dedc9fb-c576-46dc-8154-b9ee4850c9dd",
                            "uuid": "206b465c-ab25-4b48-b955-4453c9e02cf3",
                        },
                    ],
                    "router": {
                        "cases": [
                            {
                                "arguments": ["whatsapp"],
                                "category_uuid": "c09fe578-b252-4026-8ae0-5ece0762b60a",
                                "type": "has_only_phrase",
                                "uuid": "860f3841-b4a8-4010-b99d-ccdd4df3bcac",
                            }
                        ],
                        "categories": [
                            {
                                "exit_uuid": "4960c299-51c4-4f2a-addb-efa9f01da6d8",
                                "name": "WhatsApp",
                                "uuid": "c09fe578-b252-4026-8ae0-5ece0762b60a",
                            },
                            {
                                "exit_uuid": "206b465c-ab25-4b48-b955-4453c9e02cf3",
                                "name": "Other",
                                "uuid": "b8784302-6285-4b86-8b3d-7e0f845992a9",
                            },
                        ],
                        "default_category_uuid": "b8784302-6285-4b86-8b3d-7e0f845992a9",
                        "operand": "@(urn_parts(contact.urn).scheme)",
                        "result_name": "",
                        "type": "switch",
                    },
                    "uuid": "e715d7fb-28bf-425e-be3b-3b45c1bb0af0",
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
                                    "uuid": "07507934-562f-4588-9634-58f7abaa7f31",
                                },
                                {
                                    "description": "",
                                    "title": "Insatisfeito \ud83d\ude41",
                                    "uuid": "a047bf70-707f-4ddb-9009-a1bc1665d980",
                                },
                                {
                                    "description": "",
                                    "title": "Neutro \ud83d\ude36",
                                    "uuid": "f26e6521-8b6f-43da-a5da-87c1e2529f96",
                                },
                                {
                                    "description": "",
                                    "title": "Satisfeito \ud83d\ude42",
                                    "uuid": "0ea27bdb-c90c-434e-ba98-4de165e3fa3b",
                                },
                                {
                                    "description": "",
                                    "title": "Muito satisfeito \ud83d\ude03",
                                    "uuid": "c8960771-af8e-47c4-9542-5df86ca9edcc",
                                },
                            ],
                            "messageType": "interactive",
                            "quick_replies": [],
                            "text": "*Como voc\u00ea avalia o meu atendimento?* \ud83d\udc47",
                            "type": "send_whatsapp_msg",
                            "uuid": "781450c5-e6f4-4dde-a03b-51662cbd00ef",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "4dcffaa1-0674-4363-941b-4f5e3fb0a5b5",
                            "uuid": "d59f3e20-29a1-4f46-9a1f-c364a83fe617",
                        }
                    ],
                    "uuid": "2857c7ea-5e79-4b13-a73a-cfbe61ae1f6c",
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
                            "uuid": "aa9eb133-f259-41f2-83a2-74c927d7d297",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "4dcffaa1-0674-4363-941b-4f5e3fb0a5b5",
                            "uuid": "9e4cfcaa-c466-47ce-b9df-b1e59bcb4087",
                        }
                    ],
                    "uuid": "5dedc9fb-c576-46dc-8154-b9ee4850c9dd",
                },
                {
                    "actions": [
                        {
                            "attachments": [],
                            "text": "Sua opinião é muito importante para nós e leva menos de 1 minuto. Agradecemos se puder responder.",
                            "type": "send_msg",
                            "quick_replies": [],
                            "uuid": "364ccca7-a19c-4fff-bcab-34a7f24c1a14",
                        },
                        {
                            "category": "",
                            "name": "tentativa",
                            "type": "set_run_result",
                            "uuid": "30f0527c-6e69-4dc3-a73f-094cdc8200db",
                            "value": "@(results.tentativa +1)",
                        },
                    ],
                    "exits": [
                        {
                            "destination_uuid": "e715d7fb-28bf-425e-be3b-3b45c1bb0af0",
                            "uuid": "e69a4e6a-e99a-448b-be56-e43c72425c68",
                        }
                    ],
                    "uuid": "d5daf3ec-e348-481b-b0e5-2409f90b726d",
                },
                {
                    "actions": [],
                    "exits": [
                        {
                            "destination_uuid": "c9aa9cda-5e84-4ddf-88d1-4ac4039dd398",
                            "uuid": "e58afa86-e4fd-4b0a-a690-652ea3055d96",
                        },
                        {
                            "destination_uuid": "c9aa9cda-5e84-4ddf-88d1-4ac4039dd398",
                            "uuid": "25e16f79-1da4-45e0-bbdd-533d87800e18",
                        },
                        {
                            "destination_uuid": "4c7a6ce2-a47c-4a93-843c-65713a3d4ada",
                            "uuid": "0e0607a2-aa36-4bd1-99de-2c271d7b611f",
                        },
                        {
                            "destination_uuid": "85d9c83e-ed42-4a1b-aab8-f0f2b2673dc6",
                            "uuid": "d3cbf020-732f-4a7d-9cd0-4665fed74623",
                        },
                        {
                            "destination_uuid": "85d9c83e-ed42-4a1b-aab8-f0f2b2673dc6",
                            "uuid": "cfe6a86e-c4ad-4354-87aa-dee48a28b0e0",
                        },
                        {
                            "destination_uuid": "1400533b-0bd5-4466-90e1-d10828454833",
                            "uuid": "d3dfec87-b652-47f0-9772-0681811b652e",
                        },
                        {
                            "uuid": "bdd79156-2302-48f5-9f9f-01e00e9b14a7",
                            "destination_uuid": "1400533b-0bd5-4466-90e1-d10828454833",
                        },
                    ],
                    "router": {
                        "cases": [
                            {
                                "arguments": ["Muito satisfeito \ud83d\ude03"],
                                "category_uuid": "504ecab8-399c-4131-b6c2-1b5ad2551ba6",
                                "type": "has_only_phrase",
                                "uuid": "370acbd7-7295-4e47-b044-8310f989103d",
                            },
                            {
                                "arguments": ["Satisfeito \ud83d\ude42"],
                                "category_uuid": "a54c1954-c292-43e8-be21-924700fe8dc1",
                                "type": "has_only_phrase",
                                "uuid": "d965f29a-55fe-468c-8b9f-7c592d08258d",
                            },
                            {
                                "arguments": ["Neutro \ud83d\ude36"],
                                "category_uuid": "7fc56dd7-cfda-4de2-90d4-207968077f8c",
                                "type": "has_only_phrase",
                                "uuid": "1040779e-c097-4b55-9436-d5d8dc22f550",
                            },
                            {
                                "arguments": ["Insatisfeito \ud83d\ude41"],
                                "category_uuid": "b12493b3-dcbc-44a3-937b-377076d61042",
                                "type": "has_only_phrase",
                                "uuid": "560eed3b-c2b3-407a-ba70-5ec7b9e76536",
                            },
                            {
                                "arguments": ["Muito insatisfeito \ud83d\ude23"],
                                "category_uuid": "4e0e419c-57ff-4c8e-9737-f9c03a1e1f27",
                                "type": "has_only_phrase",
                                "uuid": "7ad88331-4e97-4e1e-b27c-4919210624b3",
                            },
                            {
                                "arguments": ["\u00f3timo otimo"],
                                "category_uuid": "504ecab8-399c-4131-b6c2-1b5ad2551ba6",
                                "type": "has_any_word",
                                "uuid": "4b92d027-8fd7-4c1a-b911-a953e6cf6850",
                            },
                            {
                                "arguments": ["bom boa"],
                                "category_uuid": "a54c1954-c292-43e8-be21-924700fe8dc1",
                                "type": "has_any_word",
                                "uuid": "614b6ee5-97f9-4cf2-a92c-4ef12b2d2400",
                            },
                            {
                                "arguments": ["neutro neutra normal"],
                                "category_uuid": "7fc56dd7-cfda-4de2-90d4-207968077f8c",
                                "type": "has_any_word",
                                "uuid": "dfb8c7c0-3393-4bc4-b82a-370404af6cdd",
                            },
                            {
                                "arguments": ["ruim rum"],
                                "category_uuid": "b12493b3-dcbc-44a3-937b-377076d61042",
                                "type": "has_any_word",
                                "uuid": "89cd9f22-0e86-4ebc-97e3-3e91f7f7760e",
                            },
                            {
                                "arguments": ["p\u00e9ssimo pessimo pesimo"],
                                "category_uuid": "4e0e419c-57ff-4c8e-9737-f9c03a1e1f27",
                                "type": "has_any_word",
                                "uuid": "143ff141-0735-42d2-865d-d9a77cb5c080",
                            },
                            {
                                "arguments": ["satisfeito satisfeita"],
                                "category_uuid": "a54c1954-c292-43e8-be21-924700fe8dc1",
                                "type": "has_any_word",
                                "uuid": "79baa84f-db8c-45a3-bab7-faf791fb1bc4",
                            },
                        ],
                        "categories": [
                            {
                                "exit_uuid": "e58afa86-e4fd-4b0a-a690-652ea3055d96",
                                "name": "5",
                                "uuid": "504ecab8-399c-4131-b6c2-1b5ad2551ba6",
                            },
                            {
                                "exit_uuid": "25e16f79-1da4-45e0-bbdd-533d87800e18",
                                "name": "4",
                                "uuid": "a54c1954-c292-43e8-be21-924700fe8dc1",
                            },
                            {
                                "exit_uuid": "0e0607a2-aa36-4bd1-99de-2c271d7b611f",
                                "name": "3",
                                "uuid": "7fc56dd7-cfda-4de2-90d4-207968077f8c",
                            },
                            {
                                "exit_uuid": "d3cbf020-732f-4a7d-9cd0-4665fed74623",
                                "name": "2",
                                "uuid": "b12493b3-dcbc-44a3-937b-377076d61042",
                            },
                            {
                                "exit_uuid": "cfe6a86e-c4ad-4354-87aa-dee48a28b0e0",
                                "name": "1",
                                "uuid": "4e0e419c-57ff-4c8e-9737-f9c03a1e1f27",
                            },
                            {
                                "exit_uuid": "d3dfec87-b652-47f0-9772-0681811b652e",
                                "name": "Other",
                                "uuid": "f37cf173-f489-440f-907d-dc9b52ea12e4",
                            },
                            {
                                "exit_uuid": "bdd79156-2302-48f5-9f9f-01e00e9b14a7",
                                "name": "No Response",
                                "uuid": "2dddf3fd-86f5-4f1b-9416-9622acfa64a9",
                            },
                        ],
                        "default_category_uuid": "f37cf173-f489-440f-907d-dc9b52ea12e4",
                        "operand": "@input.text",
                        "result_name": "avaliacao",
                        "type": "switch",
                        "wait": {
                            "timeout": {
                                "category_uuid": "2dddf3fd-86f5-4f1b-9416-9622acfa64a9",
                                "seconds": 600,
                            },
                            "type": "msg",
                        },
                    },
                    "uuid": "4dcffaa1-0674-4363-941b-4f5e3fb0a5b5",
                },
                {
                    "actions": [
                        {
                            "field": {
                                "key": "nota_pesquisa_atendimento_humano",
                                "name": "Nota Pesquisa Atendimento Humano",
                            },
                            "type": "set_contact_field",
                            "uuid": "41d620b0-300f-4610-8fbb-f5abd8330345",
                            "value": "@results.avaliacao.category",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "e2cfc927-abf9-4181-9c59-e09cf969c1bf",
                            "uuid": "8672429a-8767-4c22-b126-0e8c13f61fcd",
                        }
                    ],
                    "uuid": "c9aa9cda-5e84-4ddf-88d1-4ac4039dd398",
                },
                {
                    "actions": [],
                    "exits": [
                        {
                            "destination_uuid": None,
                            "uuid": "b56ec274-4a16-439c-bd7e-62aa02c3a618",
                        },
                        {
                            "destination_uuid": "d5daf3ec-e348-481b-b0e5-2409f90b726d",
                            "uuid": "bb714dce-43e1-48fc-a5b8-b0dbae0502ca",
                        },
                    ],
                    "router": {
                        "cases": [
                            {
                                "arguments": ["1"],
                                "category_uuid": "913545b2-73ca-4835-95de-ef6692f27cf2",
                                "type": "has_any_word",
                                "uuid": "bdc87d75-ac28-4aad-96b7-19bbe97b99fa",
                            }
                        ],
                        "categories": [
                            {
                                "exit_uuid": "b56ec274-4a16-439c-bd7e-62aa02c3a618",
                                "name": "J\u00e1 tentou 1x",
                                "uuid": "913545b2-73ca-4835-95de-ef6692f27cf2",
                            },
                            {
                                "exit_uuid": "bb714dce-43e1-48fc-a5b8-b0dbae0502ca",
                                "name": "Other",
                                "uuid": "e7640c78-1374-4c57-a3e5-4378283f9fd8",
                            },
                        ],
                        "default_category_uuid": "e7640c78-1374-4c57-a3e5-4378283f9fd8",
                        "operand": "@results.tentativa",
                        "type": "switch",
                    },
                    "uuid": "1400533b-0bd5-4466-90e1-d10828454833",
                },
                {
                    "uuid": "e2cfc927-abf9-4181-9c59-e09cf969c1bf",
                    "actions": [
                        {
                            "type": "set_run_result",
                            "name": "avaliacao",
                            "value": "@results.avaliacao.category",
                            "category": "@results.avaliacao.category",
                            "uuid": "1ddc320d-ec02-4d31-bed4-254166e9adcc",
                        }
                    ],
                    "exits": [
                        {
                            "uuid": "5e7a3f62-4753-485e-bf04-7271dbc55d80",
                            "destination_uuid": "1b72166c-2840-4d07-948c-f8978f428f3a",
                        }
                    ],
                },
                {
                    "actions": [
                        {
                            "field": {
                                "key": "nota_pesquisa_atendimento_humano",
                                "name": "Nota Pesquisa Atendimento Humano",
                            },
                            "type": "set_contact_field",
                            "uuid": "cf88f05b-7575-4d2a-aa9c-266be2e2b099",
                            "value": "@results.avaliacao.category",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "85d9c83e-ed42-4a1b-aab8-f0f2b2673dc6",
                            "uuid": "7b8d3a2f-0685-4468-9e46-f4cdb22e7aa4",
                        }
                    ],
                    "uuid": "4c7a6ce2-a47c-4a93-843c-65713a3d4ada",
                },
                {
                    "uuid": "1b72166c-2840-4d07-948c-f8978f428f3a",
                    "actions": [
                        {
                            "uuid": "c2a5b33d-781f-4891-bb48-5a00043476d9",
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
                                "uuid": "86ada5aa-2d58-464c-97aa-0f691c58dfa8",
                                "type": "has_only_text",
                                "arguments": ["Success"],
                                "category_uuid": "9d5f54c2-5284-407b-91df-9b95fdb47a59",
                            }
                        ],
                        "categories": [
                            {
                                "uuid": "9d5f54c2-5284-407b-91df-9b95fdb47a59",
                                "name": "Success",
                                "exit_uuid": "b77afbc0-d351-4c4e-9fcd-debd42818c69",
                            },
                            {
                                "uuid": "20ebdb7d-aca2-497e-956c-1aa6c1025ee3",
                                "name": "Failure",
                                "exit_uuid": "a1114148-ead6-4c6c-9944-5ce78cef266f",
                            },
                        ],
                        "default_category_uuid": "20ebdb7d-aca2-497e-956c-1aa6c1025ee3",
                    },
                    "exits": [
                        {
                            "uuid": "b77afbc0-d351-4c4e-9fcd-debd42818c69",
                            "destination_uuid": "ba65e658-7022-4862-94e6-e79406d5b578",
                        },
                        {
                            "uuid": "a1114148-ead6-4c6c-9944-5ce78cef266f",
                            "destination_uuid": "ba65e658-7022-4862-94e6-e79406d5b578",
                        },
                    ],
                },
                {
                    "actions": [
                        {
                            "attachments": [],
                            "quick_replies": [],
                            "text": "Deixe um coment\u00e1rio para sempre melhorarmos nosso atendimento \u270d\ufe0f",
                            "type": "send_msg",
                            "uuid": "ba177798-f428-441e-b896-0f5670ad97ee",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "49277b01-5c08-4cf3-b8d9-c979f5ca3eb3",
                            "uuid": "006b3cba-fc20-4564-bd2e-34e9cce21aae",
                        }
                    ],
                    "uuid": "85d9c83e-ed42-4a1b-aab8-f0f2b2673dc6",
                },
                {
                    "actions": [
                        {
                            "attachments": [],
                            "quick_replies": [],
                            "text": "Deixe um coment\u00e1rio sobre sua experi\u00eancia com nosso atendimento \u270d\ufe0f",
                            "type": "send_msg",
                            "uuid": "6a700f2d-3988-4e5f-8a2f-19149693dc1f",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "cb4e32e4-541e-4de6-b0f9-8ba3d433c870",
                            "uuid": "51634027-d0cb-4a69-ad15-7b54ddefada5",
                        }
                    ],
                    "uuid": "ba65e658-7022-4862-94e6-e79406d5b578",
                },
                {
                    "actions": [
                        {
                            "category": "@results.avaliacao.category",
                            "name": "avaliacao",
                            "type": "set_run_result",
                            "uuid": "2a2a5140-8bdc-43d7-9715-87fc97f3cc52",
                            "value": "@results.avaliacao.category",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "089c1a3f-be4a-46bd-8979-2d20a81e2580",
                            "uuid": "8798dbf7-f9d8-4277-b271-d89ae194c79e",
                        }
                    ],
                    "uuid": "49277b01-5c08-4cf3-b8d9-c979f5ca3eb3",
                },
                {
                    "actions": [],
                    "exits": [
                        {
                            "destination_uuid": "e943d3ed-141f-4bb4-abde-83c19e250a05",
                            "uuid": "0d753e70-d9f9-4359-85d0-3fc26f7701aa",
                        },
                        {
                            "destination_uuid": "fb652fab-817c-42b3-b0f6-19d86d80ee2d",
                            "uuid": "37b972c1-e34f-41e5-821d-1c965350ee07",
                        },
                    ],
                    "router": {
                        "cases": [],
                        "categories": [
                            {
                                "exit_uuid": "0d753e70-d9f9-4359-85d0-3fc26f7701aa",
                                "name": "All Responses",
                                "uuid": "83f9f513-ac86-4dde-8ce9-f8b4b3923388",
                            },
                            {
                                "exit_uuid": "37b972c1-e34f-41e5-821d-1c965350ee07",
                                "name": "No Response",
                                "uuid": "95029ae5-0fe5-4084-a1bd-66f8d23e6b1f",
                            },
                        ],
                        "default_category_uuid": "83f9f513-ac86-4dde-8ce9-f8b4b3923388",
                        "operand": "@input.text",
                        "result_name": "comentario",
                        "type": "switch",
                        "wait": {
                            "timeout": {
                                "category_uuid": "95029ae5-0fe5-4084-a1bd-66f8d23e6b1f",
                                "seconds": 600,
                            },
                            "type": "msg",
                        },
                    },
                    "uuid": "cb4e32e4-541e-4de6-b0f9-8ba3d433c870",
                },
                {
                    "actions": [],
                    "exits": [
                        {
                            "destination_uuid": "64cf9379-df72-4bf1-b48d-0f1729c119dc",
                            "uuid": "0d04eef2-783b-4e84-a7b2-7fe6efc2b4d1",
                        },
                        {
                            "destination_uuid": "9c829e36-8fa3-44f5-bafc-c14bddb8f653",
                            "uuid": "284e64dc-c0ed-4328-90aa-7908242c6f6b",
                        },
                    ],
                    "router": {
                        "cases": [],
                        "categories": [
                            {
                                "exit_uuid": "0d04eef2-783b-4e84-a7b2-7fe6efc2b4d1",
                                "name": "All Responses",
                                "uuid": "92e016a9-eafc-43b4-9d4d-4db7467dd6a9",
                            },
                            {
                                "exit_uuid": "284e64dc-c0ed-4328-90aa-7908242c6f6b",
                                "name": "No Response",
                                "uuid": "4d331dfa-0c06-4a7c-b8d2-2abf698f6ec8",
                            },
                        ],
                        "default_category_uuid": "92e016a9-eafc-43b4-9d4d-4db7467dd6a9",
                        "operand": "@input.text",
                        "result_name": "comentario",
                        "type": "switch",
                        "wait": {
                            "timeout": {
                                "category_uuid": "4d331dfa-0c06-4a7c-b8d2-2abf698f6ec8",
                                "seconds": 600,
                            },
                            "type": "msg",
                        },
                    },
                    "uuid": "089c1a3f-be4a-46bd-8979-2d20a81e2580",
                },
                {
                    "actions": [
                        {
                            "attachments": [],
                            "quick_replies": [],
                            "text": "Seu atendimento foi finalizado.\n\nAgradecemos a sua colabora\u00e7\u00e3o. At\u00e9 a pr\u00f3xima \ud83d\udc4b",
                            "type": "send_msg",
                            "uuid": "d3dbf5c4-6404-47b8-a0a8-c739266e82f4",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "f9066628-7ec1-465e-bdfe-d9dd90838926",
                            "uuid": "a63e4afd-edfd-4cf7-9221-70b3c9dea944",
                        }
                    ],
                    "uuid": "e943d3ed-141f-4bb4-abde-83c19e250a05",
                },
                {
                    "actions": [
                        {
                            "category": "N\u00e3o respondente",
                            "name": "comentario",
                            "type": "set_run_result",
                            "uuid": "aaf24105-4e5b-4f82-8d7c-9509cbcd6e49",
                            "value": "N\u00e3o respondente",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "f9066628-7ec1-465e-bdfe-d9dd90838926",
                            "uuid": "27ac1b53-d4be-4618-b435-79532dadb24e",
                        }
                    ],
                    "uuid": "fb652fab-817c-42b3-b0f6-19d86d80ee2d",
                },
                {
                    "actions": [
                        {
                            "attachments": [],
                            "quick_replies": [],
                            "text": "Seu atendimento foi finalizado. Iremos analisar seu coment\u00e1rio com responsabilidade. \n\nAgradecemos a sua colabora\u00e7\u00e3o para melhorar o atendimento. At\u00e9 a pr\u00f3xima \ud83d\udc4b",
                            "type": "send_msg",
                            "uuid": "87033018-daf3-45ff-a85e-92f184491528",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "f9066628-7ec1-465e-bdfe-d9dd90838926",
                            "uuid": "17ef70f7-0ebe-44b8-a388-e58ead851d59",
                        }
                    ],
                    "uuid": "64cf9379-df72-4bf1-b48d-0f1729c119dc",
                },
                {
                    "actions": [
                        {
                            "category": "N\u00e3o respondente",
                            "name": "comentario",
                            "type": "set_run_result",
                            "uuid": "48956fb3-06b9-4506-8906-a5f172d6aaff",
                            "value": "N\u00e3o respondente",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "f9066628-7ec1-465e-bdfe-d9dd90838926",
                            "uuid": "7fd590e1-918d-48dc-a893-c4315eafd20a",
                        }
                    ],
                    "uuid": "9c829e36-8fa3-44f5-bafc-c14bddb8f653",
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
                            "uuid": "28e30d2d-6bb8-4c1f-8d69-80a4cf74071e",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": None,
                            "uuid": "f34268ea-ce60-41ec-a4b8-b89c11352a0b",
                        },
                        {
                            "destination_uuid": None,
                            "uuid": "5642ed73-5e06-47ad-8c24-037d56b0c9db",
                        },
                    ],
                    "router": {
                        "cases": [
                            {
                                "arguments": ["Success"],
                                "category_uuid": "2de26bc7-504b-4d55-8a25-b0d842f3bcf5",
                                "type": "has_only_text",
                                "uuid": "883ca4c4-c0ad-400c-97a5-b727f852cfc4",
                            }
                        ],
                        "categories": [
                            {
                                "exit_uuid": "f34268ea-ce60-41ec-a4b8-b89c11352a0b",
                                "name": "Success",
                                "uuid": "2de26bc7-504b-4d55-8a25-b0d842f3bcf5",
                            },
                            {
                                "exit_uuid": "5642ed73-5e06-47ad-8c24-037d56b0c9db",
                                "name": "Failure",
                                "uuid": "02123643-746d-47c3-9ac5-4e2da0bd965f",
                            },
                        ],
                        "default_category_uuid": "02123643-746d-47c3-9ac5-4e2da0bd965f",
                        "operand": "@results.result.category",
                        "type": "switch",
                    },
                    "uuid": "f9066628-7ec1-465e-bdfe-d9dd90838926",
                },
            ],
            "spec_version": "13.1.0",
            "type": "messaging",
            "uuid": "4cb6a944-48d2-4b2c-834c-0f9f6f480917",
            "revision": 34,
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
