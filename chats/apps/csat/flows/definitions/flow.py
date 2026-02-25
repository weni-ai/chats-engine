CSAT_FLOW_VERSION = 5
CSAT_FLOW_NAME = "Weni Chats CSAT Flow"
CSAT_FLOW_DEFINITION_DATA = {
    "version": "13",
    "site": "https://flows.weni.ai",
    "flows": [
        {
            "_ui": {
                "nodes": {
                    "e9e18143-46c6-415a-8762-31e0c80948c7": {
                        "position": {
                            "left": "1299.1081235854301",
                            "top": "1012.9467090587792",
                        },
                        "type": "execute_actions",
                    },
                    "4e2ef0e1-4ce1-41fe-8f48-2f514845da90": {
                        "type": "split_by_scheme",
                        "position": {
                            "left": "1291.606616390819",
                            "top": "1198.2193016513718",
                        },
                        "config": {"cases": {}},
                    },
                    "acac72a3-54cb-4346-b34a-a7b29c659fa5": {
                        "position": {
                            "left": "1138.6081235854301",
                            "top": "1390.4637460958163",
                        },
                        "type": "execute_actions",
                    },
                    "0096b75c-0757-48bb-ae81-5e8b1ee5e972": {
                        "position": {
                            "left": "1523.6081235854301",
                            "top": "1418.253375725446",
                        },
                        "type": "execute_actions",
                    },
                    "824f2b51-a07d-4866-bae6-2dfd0ce1e35f": {
                        "position": {
                            "left": "1936.2771606224667",
                            "top": "1596.63144979952",
                        },
                        "type": "execute_actions",
                    },
                    "183b5ca1-6a25-40fb-b0cd-8386aa20ae34": {
                        "position": {
                            "left": "2301.5796791409853",
                            "top": "1605.3641905402608",
                        },
                        "type": "execute_actions",
                    },
                    "4a2add18-fa07-4072-a953-e0545ab48487": {
                        "position": {
                            "left": "1135.002130439344",
                            "top": "1681.275597947668",
                        },
                        "type": "execute_actions",
                    },
                    "3e1bc812-75c9-4609-909d-dd7c0d3abc7c": {
                        "position": {
                            "left": "1537.7174976978713",
                            "top": "1681.275597947668",
                        },
                        "type": "execute_actions",
                    },
                    "e559cade-3d77-4bd4-a033-ffec5ebcd190": {
                        "config": {"cases": {}},
                        "position": {
                            "left": "1157.2408609900526",
                            "top": "2031.653596440618",
                        },
                        "type": "wait_for_response",
                    },
                    "61459888-cab1-4ac4-9664-61f08756f9cb": {
                        "type": "split_by_scheme",
                        "position": {
                            "left": "2273.6661976595033",
                            "top": "2103.426954559354",
                        },
                        "config": {"cases": {}},
                    },
                    "24e5fb95-1e1f-4663-ba85-4a735bed09dd": {
                        "position": {
                            "left": "516.5389376101214",
                            "top": "2184.638408866735",
                        },
                        "type": "execute_actions",
                    },
                    "36168769-7912-45dd-9ece-9848ea012e8a": {
                        "config": {
                            "cases": {},
                            "operand": {
                                "id": "tentativa",
                                "name": "tentativa",
                                "type": "result",
                            },
                        },
                        "position": {
                            "left": "1891.1479072905554",
                            "top": "2308.100212814713",
                        },
                        "type": "split_by_run_result",
                    },
                    "cdd48623-48db-4836-b4a3-fd32ac276d8a": {
                        "position": {"left": 521, "top": 2346},
                        "type": "execute_actions",
                    },
                    "c7008052-12e1-425b-9d83-9ec6d156f9fb": {
                        "position": {
                            "left": "1243.6657730270365",
                            "top": "2384.993941290002",
                        },
                        "type": "execute_actions",
                    },
                    "69d4d33f-bbad-44cc-816c-23a2895ca36b": {
                        "position": {
                            "left": "1953.4541909411892",
                            "top": "2453.210412762483",
                        },
                        "type": "execute_actions",
                    },
                    "97f7d325-128d-42e2-b378-27e7429e4515": {
                        "config": {},
                        "position": {"left": "530.5389376101214", "top": 2563},
                        "type": "split_by_webhook",
                    },
                    "795656c5-c260-4711-ad8e-f842b38a01fa": {
                        "config": {},
                        "position": {
                            "left": "1248.6657730270365",
                            "top": "2682.993941290002",
                        },
                        "type": "split_by_webhook",
                    },
                    "f119a4c1-43dc-42a4-a19d-6875681f32d9": {
                        "position": {"left": "531.1525515926652", "top": 2784},
                        "type": "execute_actions",
                    },
                    "a698e8e8-cdba-4a8e-ad88-d3e9c63575a7": {
                        "config": {"cases": {}},
                        "position": {
                            "left": "525.4199459661597",
                            "top": "2963.3440877475277",
                        },
                        "type": "wait_for_response",
                    },
                    "83fd6281-3051-4452-9749-e15dc6bc9f95": {
                        "position": {
                            "left": "1245.9127841724944",
                            "top": "2969.993941290002",
                        },
                        "type": "execute_actions",
                    },
                    "8ead47fc-6ace-487d-8268-9c658abdeade": {
                        "config": {"cases": {}},
                        "position": {
                            "left": "1262.3460900709856",
                            "top": "3166.571929565236",
                        },
                        "type": "wait_for_response",
                    },
                    "391f1a65-79aa-4927-8ebd-5f3262e61d20": {
                        "position": {
                            "left": "476.41994596615973",
                            "top": "3216.3440877475277",
                        },
                        "type": "execute_actions",
                    },
                    "58d7e185-fa65-40de-b37c-f1a1c112b660": {
                        "position": {
                            "left": "796.927464564468",
                            "top": "3224.6395402223325",
                        },
                        "type": "execute_actions",
                    },
                    "fca21cac-795d-42a6-9bc3-daa140fee450": {
                        "position": {
                            "left": "1215.3460900709856",
                            "top": "3401.4251190743635",
                        },
                        "type": "execute_actions",
                    },
                    "09212661-8055-4bdf-ae23-3d3b6667632f": {
                        "position": {
                            "left": "1479.7303603839714",
                            "top": "3403.84381983449",
                        },
                        "type": "execute_actions",
                    },
                    "9f3b308e-478c-4921-88b4-e72f737db459": {
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
                    "20eabe20-4978-47fc-8312-64eac1f9159b": {
                        "description": [""],
                        "title": ["Satisfied \ud83d\ude42"],
                    },
                    "2e7b3859-2b88-432e-8cc1-f4f74afb212d": {
                        "description": [""],
                        "title": ["Neutral \ud83d\ude36"],
                    },
                    "3a62144c-dbbb-4a58-97d5-ce50f9e6e7de": {
                        "description": [""],
                        "title": ["Dissatisfied \ud83d\ude41"],
                    },
                    "3ece2fd7-3c72-4f72-a31e-417ad0dea0e2": {
                        "button_text": ["Select here"],
                        "footer": [
                            "It\u2019s very quick, it won\u2019t even take a minute."
                        ],
                        "header_text": ["Customer Satisfaction Survey"],
                        "quick_replies": [],
                        "text": ["*How would you rate my service?* \ud83d\udc47"],
                    },
                    "4b9f431f-e28e-44b1-8307-12911f0c98a0": {
                        "arguments": ["Dissatisfied \ud83d\ude41"]
                    },
                    "5786b49c-a7de-43f2-b622-7aac3d725874": {
                        "description": [""],
                        "title": ["Very satisfied \ud83d\ude03"],
                    },
                    "58c3086c-2936-46e5-8fd5-498c47cccc05": {
                        "attachments": [],
                        "text": [
                            "Your session has ended.\n\nThank you for your feedback. See you next time! \ud83d\udc4b"
                        ],
                    },
                    "5b16573d-05c6-487f-8ea7-f76581acb8b9": {
                        "arguments": ["Satisfied \ud83d\ude42"]
                    },
                    "71880b13-5e44-4626-91af-0f52a549ae47": {
                        "attachments": [],
                        "text": [
                            "Your session has ended. We will carefully review your feedback.\n\nThank you for helping us improve our service. See you next time! \ud83d\udc4b"
                        ],
                    },
                    "889465a8-8ce1-4ea1-a42e-59e38ed862e5": {"arguments": ["good"]},
                    "8f997a95-6658-43de-8939-95625a638cc9": {
                        "attachments": [],
                        "text": [
                            "Your opinion is very important to us and takes less than 1 minute. We appreciate it if you can respond."
                        ],
                    },
                    "93402ab5-99ea-4e4e-b5af-d8df66e220ac": {
                        "arguments": ["Very satisfied \ud83d\ude03"]
                    },
                    "938aadd0-8e29-4e04-b529-9b3747e309c7": {
                        "arguments": ["terrible horrible"]
                    },
                    "96c2383e-dc3d-4e55-a091-64e9b22eb7af": {
                        "attachments": [],
                        "text": ["Before finishing, tell us about your experience!"],
                    },
                    "9aa64964-5423-4fcc-ae4b-318e7dd3fb15": {
                        "description": [""],
                        "title": ["Very dissatisfied \ud83d\ude23"],
                    },
                    "b2a1bde6-41a4-46cb-8c9a-9d64bfad6e99": {
                        "arguments": ["satisfied"]
                    },
                    "b62f8f9b-4b10-4db9-80f1-90a1a43d97e8": {
                        "attachments": [],
                        "text": [
                            "Leave a comment so we can keep improving our service \u270d\ufe0f"
                        ],
                    },
                    "b9ab6618-7da9-4749-88ff-0c6e07ce1c8e": {
                        "arguments": ["neutral normal ok"]
                    },
                    "bdc272ef-0a4c-4b1f-9a78-04cb216ce3ec": {
                        "arguments": ["Neutral \ud83d\ude36"]
                    },
                    "d4db6355-9669-4a4f-87dd-e42872d7b41c": {"arguments": ["great"]},
                    "d70ddf36-b0cf-44e7-b394-020a63300e1e": {
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
                    "e7c04b3c-6112-4d12-97f1-0eaafd38c74d": {
                        "attachments": [],
                        "text": [
                            "Leave a comment about your experience with our service \u270d\ufe0f"
                        ],
                    },
                    "ef5ef052-76d6-4018-b2b6-17a1b2e706f8": {
                        "arguments": ["Very dissatisfied \ud83d\ude23"]
                    },
                    "f3c1a0dd-a7c3-466e-8038-2a64074aafd8": {"arguments": ["bad poor"]},
                    "a5ff4115-74de-4646-8bdb-bcf8a1743eb0": {
                        "text": ["Before finishing, tell us about your experience!"],
                        "quick_replies": [],
                    },
                    "83a33385-1f5b-43e4-9c60-ae2f18402578": {
                        "text": ["Before finishing, tell us about your experience!"],
                        "attachments": [],
                    },
                    "4c6d48cb-7b5a-4a80-a72b-fcdfc7bf3519": {
                        "text": [
                            "Your opinion is very important to us and takes less than 1 minute. We appreciate it if you can respond."
                        ],
                        "quick_replies": [],
                    },
                    "5e0db7b2-f594-4483-9e3c-c4cb896d2503": {
                        "text": [
                            "Your opinion is very important to us and takes less than 1 minute. We appreciate it if you can respond."
                        ],
                        "attachments": [],
                    },
                },
                "por": {
                    "20eabe20-4978-47fc-8312-64eac1f9159b": {
                        "description": [""],
                        "title": ["Satisfeito \ud83d\ude42"],
                    },
                    "2e7b3859-2b88-432e-8cc1-f4f74afb212d": {
                        "description": [""],
                        "title": ["Neutro \ud83d\ude36"],
                    },
                    "3a62144c-dbbb-4a58-97d5-ce50f9e6e7de": {
                        "description": [""],
                        "title": ["Insatisfeito \ud83d\ude41"],
                    },
                    "3ece2fd7-3c72-4f72-a31e-417ad0dea0e2": {"quick_replies": []},
                    "5786b49c-a7de-43f2-b622-7aac3d725874": {
                        "description": [""],
                        "title": ["Muito satisfeito \ud83d\ude03"],
                    },
                    "58c3086c-2936-46e5-8fd5-498c47cccc05": {"attachments": []},
                    "71880b13-5e44-4626-91af-0f52a549ae47": {"attachments": []},
                    "8f997a95-6658-43de-8939-95625a638cc9": {"attachments": []},
                    "9aa64964-5423-4fcc-ae4b-318e7dd3fb15": {
                        "description": [""],
                        "title": ["Muito insatisfeito \ud83d\ude23"],
                    },
                    "b62f8f9b-4b10-4db9-80f1-90a1a43d97e8": {"attachments": []},
                    "d70ddf36-b0cf-44e7-b394-020a63300e1e": {"attachments": []},
                    "e7c04b3c-6112-4d12-97f1-0eaafd38c74d": {"attachments": []},
                },
                "spa": {
                    "20eabe20-4978-47fc-8312-64eac1f9159b": {
                        "description": [""],
                        "title": ["Satisfecho \ud83d\ude42"],
                    },
                    "2e7b3859-2b88-432e-8cc1-f4f74afb212d": {
                        "description": [""],
                        "title": ["Neutral \ud83d\ude36"],
                    },
                    "3a62144c-dbbb-4a58-97d5-ce50f9e6e7de": {
                        "description": [""],
                        "title": ["Insatisfecho \ud83d\ude41"],
                    },
                    "3ece2fd7-3c72-4f72-a31e-417ad0dea0e2": {
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
                    "4b9f431f-e28e-44b1-8307-12911f0c98a0": {
                        "arguments": ["Insatisfecho \ud83d\ude41"]
                    },
                    "5786b49c-a7de-43f2-b622-7aac3d725874": {
                        "description": [""],
                        "title": ["Muy satisfecho \ud83d\ude03"],
                    },
                    "58c3086c-2936-46e5-8fd5-498c47cccc05": {
                        "attachments": [],
                        "text": [
                            "Tu atenci\u00f3n ha finalizado.\n\nAgradecemos tu colaboraci\u00f3n. \u00a1Hasta la pr\u00f3xima! \ud83d\udc4b"
                        ],
                    },
                    "5b16573d-05c6-487f-8ea7-f76581acb8b9": {
                        "arguments": ["Satisfecho \ud83d\ude42"]
                    },
                    "71880b13-5e44-4626-91af-0f52a549ae47": {
                        "attachments": [],
                        "text": [
                            "Tu atenci\u00f3n ha finalizado. Analizaremos tu comentario con responsabilidad.\n\nGracias por ayudarnos a mejorar nuestra atenci\u00f3n. \u00a1Hasta la pr\u00f3xima! \ud83d\udc4b"
                        ],
                    },
                    "889465a8-8ce1-4ea1-a42e-59e38ed862e5": {
                        "arguments": ["bueno buena"]
                    },
                    "8f997a95-6658-43de-8939-95625a638cc9": {
                        "attachments": [],
                        "text": [
                            "Su opini\u00f3n es muy importante para nosotros y le tomar\u00e1 menos de 1 minuto. Le agradecemos si puede responder."
                        ],
                    },
                    "93402ab5-99ea-4e4e-b5af-d8df66e220ac": {
                        "arguments": ["Muy satisfecho \ud83d\ude03"]
                    },
                    "938aadd0-8e29-4e04-b529-9b3747e309c7": {
                        "arguments": ["horrible terrible"]
                    },
                    "96c2383e-dc3d-4e55-a091-64e9b22eb7af": {
                        "attachments": [],
                        "text": [
                            "Antes de finalizar, cu\u00e9ntanos c\u00f3mo fue tu experiencia."
                        ],
                    },
                    "9aa64964-5423-4fcc-ae4b-318e7dd3fb15": {
                        "description": [""],
                        "title": ["Muy insatisfecho \ud83d\ude23"],
                    },
                    "b2a1bde6-41a4-46cb-8c9a-9d64bfad6e99": {
                        "arguments": ["satisfecho satisfecha"]
                    },
                    "b62f8f9b-4b10-4db9-80f1-90a1a43d97e8": {
                        "attachments": [],
                        "text": [
                            "D\u00e9janos un comentario para que podamos seguir mejorando nuestra atenci\u00f3n \u270d\ufe0f"
                        ],
                    },
                    "b9ab6618-7da9-4749-88ff-0c6e07ce1c8e": {
                        "arguments": ["normal neutral"]
                    },
                    "bdc272ef-0a4c-4b1f-9a78-04cb216ce3ec": {
                        "arguments": ["Neutral \ud83d\ude36"]
                    },
                    "d4db6355-9669-4a4f-87dd-e42872d7b41c": {
                        "arguments": ["excelente"]
                    },
                    "d70ddf36-b0cf-44e7-b394-020a63300e1e": {
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
                    "e7c04b3c-6112-4d12-97f1-0eaafd38c74d": {
                        "attachments": [],
                        "text": [
                            "D\u00e9janos un comentario sobre tu experiencia con nuestra atenci\u00f3n \u270d\ufe0f"
                        ],
                    },
                    "ef5ef052-76d6-4018-b2b6-17a1b2e706f8": {
                        "arguments": ["Muy insatisfecho \ud83d\ude23"]
                    },
                    "f3c1a0dd-a7c3-466e-8038-2a64074aafd8": {
                        "arguments": ["malo mala"]
                    },
                    "a5ff4115-74de-4646-8bdb-bcf8a1743eb0": {
                        "text": [
                            "Antes de finalizar, cu\u00e9ntanos c\u00f3mo fue tu experiencia!"
                        ],
                        "quick_replies": [],
                    },
                    "83a33385-1f5b-43e4-9c60-ae2f18402578": {
                        "text": [
                            "Antes de finalizar, cu\u00e9ntanos c\u00f3mo fue tu experiencia!"
                        ],
                        "attachments": [],
                    },
                    "4c6d48cb-7b5a-4a80-a72b-fcdfc7bf3519": {
                        "text": [
                            "Su opini\u00f3n es muy importante para nosotros y le tomar\u00e1 menos de 1 minuto. Le agradecemos si puede responder."
                        ],
                        "quick_replies": [],
                    },
                    "5e0db7b2-f594-4483-9e3c-c4cb896d2503": {
                        "text": [
                            "Su opini\u00f3n es muy importante para nosotros y le tomar\u00e1 menos de 1 minuto. Le agradecemos si puede responder."
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
                            "uuid": "d64d3457-f5a2-4d86-90d0-82a171048782",
                            "value": "0",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "4e2ef0e1-4ce1-41fe-8f48-2f514845da90",
                            "uuid": "904e35e8-a04d-40fc-887e-bc727e0905a1",
                        }
                    ],
                    "uuid": "e9e18143-46c6-415a-8762-31e0c80948c7",
                },
                {
                    "uuid": "4e2ef0e1-4ce1-41fe-8f48-2f514845da90",
                    "actions": [],
                    "router": {
                        "type": "switch",
                        "cases": [
                            {
                                "uuid": "2189ea91-19a5-4cea-bedf-b11ec55d68d1",
                                "type": "has_only_phrase",
                                "arguments": ["whatsapp"],
                                "category_uuid": "02d117b0-73bd-497e-949b-ddf1064efdf4",
                            }
                        ],
                        "categories": [
                            {
                                "exit_uuid": "ea717edc-13be-414a-95b5-c13a9d949a06",
                                "name": "WhatsApp",
                                "uuid": "02d117b0-73bd-497e-949b-ddf1064efdf4",
                            },
                            {
                                "exit_uuid": "1cdc8afe-ea4a-4a99-bbda-12aad85e2453",
                                "name": "Other",
                                "uuid": "b0bcbb04-6dde-45b1-9f3b-e8ea8a764a44",
                            },
                        ],
                        "default_category_uuid": "b0bcbb04-6dde-45b1-9f3b-e8ea8a764a44",
                        "operand": "@(urn_parts(contact.urn).scheme)",
                        "result_name": "",
                    },
                    "exits": [
                        {
                            "destination_uuid": "acac72a3-54cb-4346-b34a-a7b29c659fa5",
                            "uuid": "ea717edc-13be-414a-95b5-c13a9d949a06",
                        },
                        {
                            "destination_uuid": "0096b75c-0757-48bb-ae81-5e8b1ee5e972",
                            "uuid": "1cdc8afe-ea4a-4a99-bbda-12aad85e2453",
                        },
                    ],
                },
                {
                    "uuid": "acac72a3-54cb-4346-b34a-a7b29c659fa5",
                    "actions": [
                        {
                            "type": "send_whatsapp_msg",
                            "text": "Antes de encerrar, conte como foi sua experi\u00eancia!",
                            "messageType": "simple",
                            "header_type": "media",
                            "uuid": "a5ff4115-74de-4646-8bdb-bcf8a1743eb0",
                            "flow_data": {},
                            "flow_data_attachment_name_map": {},
                            "quick_replies": [],
                        }
                    ],
                    "exits": [
                        {
                            "uuid": "4dc2b674-e910-431a-9fb4-94d444681186",
                            "destination_uuid": "4a2add18-fa07-4072-a953-e0545ab48487",
                        }
                    ],
                },
                {
                    "uuid": "0096b75c-0757-48bb-ae81-5e8b1ee5e972",
                    "actions": [
                        {
                            "attachments": [],
                            "text": "Antes de encerrar, conte como foi sua experi\u00eancia!",
                            "type": "send_msg",
                            "quick_replies": [],
                            "uuid": "83a33385-1f5b-43e4-9c60-ae2f18402578",
                        }
                    ],
                    "exits": [
                        {
                            "uuid": "ecd6ba90-b1ca-4a6d-b01c-a087c61cc0d1",
                            "destination_uuid": "3e1bc812-75c9-4609-909d-dd7c0d3abc7c",
                        }
                    ],
                },
                {
                    "uuid": "824f2b51-a07d-4866-bae6-2dfd0ce1e35f",
                    "actions": [
                        {
                            "type": "send_whatsapp_msg",
                            "text": "Sua opini\u00e3o \u00e9 muito importante para n\u00f3s e leva menos de 1 minuto. Agradecemos se puder responder.",
                            "messageType": "simple",
                            "header_type": "media",
                            "uuid": "4c6d48cb-7b5a-4a80-a72b-fcdfc7bf3519",
                            "flow_data": {},
                            "flow_data_attachment_name_map": {},
                            "quick_replies": [],
                        }
                    ],
                    "exits": [
                        {
                            "uuid": "5cb2a03a-d3b0-403c-97da-0d9f20647822",
                            "destination_uuid": "4a2add18-fa07-4072-a953-e0545ab48487",
                        }
                    ],
                },
                {
                    "uuid": "183b5ca1-6a25-40fb-b0cd-8386aa20ae34",
                    "actions": [
                        {
                            "attachments": [],
                            "text": "Sua opini\u00e3o \u00e9 muito importante para n\u00f3s e leva menos de 1 minuto. Agradecemos se puder responder.",
                            "type": "send_msg",
                            "quick_replies": [],
                            "uuid": "5e0db7b2-f594-4483-9e3c-c4cb896d2503",
                        }
                    ],
                    "exits": [
                        {
                            "uuid": "becb91ec-5ee9-4a49-a547-e5c1b7fbe215",
                            "destination_uuid": "3e1bc812-75c9-4609-909d-dd7c0d3abc7c",
                        }
                    ],
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
                                    "uuid": "9aa64964-5423-4fcc-ae4b-318e7dd3fb15",
                                },
                                {
                                    "description": "",
                                    "title": "Insatisfeito \ud83d\ude41",
                                    "uuid": "3a62144c-dbbb-4a58-97d5-ce50f9e6e7de",
                                },
                                {
                                    "description": "",
                                    "title": "Neutro \ud83d\ude36",
                                    "uuid": "2e7b3859-2b88-432e-8cc1-f4f74afb212d",
                                },
                                {
                                    "description": "",
                                    "title": "Satisfeito \ud83d\ude42",
                                    "uuid": "20eabe20-4978-47fc-8312-64eac1f9159b",
                                },
                                {
                                    "description": "",
                                    "title": "Muito satisfeito \ud83d\ude03",
                                    "uuid": "5786b49c-a7de-43f2-b622-7aac3d725874",
                                },
                            ],
                            "messageType": "interactive",
                            "quick_replies": [],
                            "text": "*Como voc\u00ea avalia o meu atendimento?* \ud83d\udc47",
                            "type": "send_whatsapp_msg",
                            "uuid": "3ece2fd7-3c72-4f72-a31e-417ad0dea0e2",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "e559cade-3d77-4bd4-a033-ffec5ebcd190",
                            "uuid": "16cc5115-8a0e-44ea-b1eb-65c3afbba4e8",
                        }
                    ],
                    "uuid": "4a2add18-fa07-4072-a953-e0545ab48487",
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
                            "uuid": "d70ddf36-b0cf-44e7-b394-020a63300e1e",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "e559cade-3d77-4bd4-a033-ffec5ebcd190",
                            "uuid": "01b38d5e-8538-4031-8b03-fe526eea4ecf",
                        }
                    ],
                    "uuid": "3e1bc812-75c9-4609-909d-dd7c0d3abc7c",
                },
                {
                    "actions": [],
                    "exits": [
                        {
                            "destination_uuid": "24e5fb95-1e1f-4663-ba85-4a735bed09dd",
                            "uuid": "ba75049b-7e64-4ddb-872e-9f9931604050",
                        },
                        {
                            "destination_uuid": "24e5fb95-1e1f-4663-ba85-4a735bed09dd",
                            "uuid": "fc39bb23-0341-4910-be67-3a17578fd58b",
                        },
                        {
                            "destination_uuid": "c7008052-12e1-425b-9d83-9ec6d156f9fb",
                            "uuid": "63ebaf6d-6384-4b23-8fea-dc1137fcbccf",
                        },
                        {
                            "destination_uuid": "c7008052-12e1-425b-9d83-9ec6d156f9fb",
                            "uuid": "238a3dd4-77bb-4952-90d2-aa731146a816",
                        },
                        {
                            "destination_uuid": "c7008052-12e1-425b-9d83-9ec6d156f9fb",
                            "uuid": "74cd8a41-be9a-46f1-a11f-4cd24ef63572",
                        },
                        {
                            "destination_uuid": "36168769-7912-45dd-9ece-9848ea012e8a",
                            "uuid": "e2b35a19-8bd6-4a2f-aacb-3d197a5ed2bb",
                        },
                        {
                            "destination_uuid": "36168769-7912-45dd-9ece-9848ea012e8a",
                            "uuid": "2da06de6-7074-45c2-ae67-f33243fd23ce",
                        },
                    ],
                    "router": {
                        "cases": [
                            {
                                "arguments": ["Muito satisfeito \ud83d\ude03"],
                                "category_uuid": "a02975fe-0afb-4424-8d87-8e217adce337",
                                "type": "has_only_phrase",
                                "uuid": "93402ab5-99ea-4e4e-b5af-d8df66e220ac",
                            },
                            {
                                "arguments": ["Satisfeito \ud83d\ude42"],
                                "category_uuid": "2e655518-35b8-4614-93f2-1bbb455c57d9",
                                "type": "has_only_phrase",
                                "uuid": "5b16573d-05c6-487f-8ea7-f76581acb8b9",
                            },
                            {
                                "arguments": ["Neutro \ud83d\ude36"],
                                "category_uuid": "abc26cc3-0429-4801-af4f-2b7d6d81b84d",
                                "type": "has_only_phrase",
                                "uuid": "bdc272ef-0a4c-4b1f-9a78-04cb216ce3ec",
                            },
                            {
                                "arguments": ["Insatisfeito \ud83d\ude41"],
                                "category_uuid": "10d49768-c55d-4f8d-bf50-bd65b87ae4b7",
                                "type": "has_only_phrase",
                                "uuid": "4b9f431f-e28e-44b1-8307-12911f0c98a0",
                            },
                            {
                                "arguments": ["Muito insatisfeito \ud83d\ude23"],
                                "category_uuid": "766c7cb3-348f-4a46-bb45-cef6a1557726",
                                "type": "has_only_phrase",
                                "uuid": "ef5ef052-76d6-4018-b2b6-17a1b2e706f8",
                            },
                            {
                                "arguments": ["\u00f3timo otimo"],
                                "category_uuid": "a02975fe-0afb-4424-8d87-8e217adce337",
                                "type": "has_any_word",
                                "uuid": "d4db6355-9669-4a4f-87dd-e42872d7b41c",
                            },
                            {
                                "arguments": ["bom boa"],
                                "category_uuid": "2e655518-35b8-4614-93f2-1bbb455c57d9",
                                "type": "has_any_word",
                                "uuid": "889465a8-8ce1-4ea1-a42e-59e38ed862e5",
                            },
                            {
                                "arguments": ["neutro neutra normal"],
                                "category_uuid": "abc26cc3-0429-4801-af4f-2b7d6d81b84d",
                                "type": "has_any_word",
                                "uuid": "b9ab6618-7da9-4749-88ff-0c6e07ce1c8e",
                            },
                            {
                                "arguments": ["ruim rum"],
                                "category_uuid": "10d49768-c55d-4f8d-bf50-bd65b87ae4b7",
                                "type": "has_any_word",
                                "uuid": "f3c1a0dd-a7c3-466e-8038-2a64074aafd8",
                            },
                            {
                                "arguments": ["p\u00e9ssimo pessimo pesimo"],
                                "category_uuid": "766c7cb3-348f-4a46-bb45-cef6a1557726",
                                "type": "has_any_word",
                                "uuid": "938aadd0-8e29-4e04-b529-9b3747e309c7",
                            },
                            {
                                "arguments": ["satisfeito satisfeita"],
                                "category_uuid": "2e655518-35b8-4614-93f2-1bbb455c57d9",
                                "type": "has_any_word",
                                "uuid": "b2a1bde6-41a4-46cb-8c9a-9d64bfad6e99",
                            },
                        ],
                        "categories": [
                            {
                                "exit_uuid": "ba75049b-7e64-4ddb-872e-9f9931604050",
                                "name": "5",
                                "uuid": "a02975fe-0afb-4424-8d87-8e217adce337",
                            },
                            {
                                "exit_uuid": "fc39bb23-0341-4910-be67-3a17578fd58b",
                                "name": "4",
                                "uuid": "2e655518-35b8-4614-93f2-1bbb455c57d9",
                            },
                            {
                                "exit_uuid": "63ebaf6d-6384-4b23-8fea-dc1137fcbccf",
                                "name": "3",
                                "uuid": "abc26cc3-0429-4801-af4f-2b7d6d81b84d",
                            },
                            {
                                "exit_uuid": "238a3dd4-77bb-4952-90d2-aa731146a816",
                                "name": "2",
                                "uuid": "10d49768-c55d-4f8d-bf50-bd65b87ae4b7",
                            },
                            {
                                "exit_uuid": "74cd8a41-be9a-46f1-a11f-4cd24ef63572",
                                "name": "1",
                                "uuid": "766c7cb3-348f-4a46-bb45-cef6a1557726",
                            },
                            {
                                "exit_uuid": "e2b35a19-8bd6-4a2f-aacb-3d197a5ed2bb",
                                "name": "Other",
                                "uuid": "fe326136-9057-4e07-9d45-aad5fca4aa0d",
                            },
                            {
                                "exit_uuid": "2da06de6-7074-45c2-ae67-f33243fd23ce",
                                "name": "No Response",
                                "uuid": "8d97e2f8-4758-4a12-ab56-a00e02a0c6dc",
                            },
                        ],
                        "default_category_uuid": "fe326136-9057-4e07-9d45-aad5fca4aa0d",
                        "operand": "@input.text",
                        "result_name": "avaliacao",
                        "type": "switch",
                        "wait": {
                            "timeout": {
                                "category_uuid": "8d97e2f8-4758-4a12-ab56-a00e02a0c6dc",
                                "seconds": 600,
                            },
                            "type": "msg",
                        },
                    },
                    "uuid": "e559cade-3d77-4bd4-a033-ffec5ebcd190",
                },
                {
                    "uuid": "61459888-cab1-4ac4-9664-61f08756f9cb",
                    "actions": [],
                    "router": {
                        "type": "switch",
                        "cases": [
                            {
                                "uuid": "93a2cac9-6a46-4b20-b03b-11778f901cb4",
                                "type": "has_only_phrase",
                                "arguments": ["whatsapp"],
                                "category_uuid": "f3d1f619-a585-4221-a2eb-94e00bfc5fe1",
                            }
                        ],
                        "categories": [
                            {
                                "uuid": "f3d1f619-a585-4221-a2eb-94e00bfc5fe1",
                                "name": "WhatsApp",
                                "exit_uuid": "ba6d7030-72fe-4e32-8374-b4a81b830851",
                            },
                            {
                                "uuid": "52c54933-7658-4d49-a453-04c3c6541b59",
                                "name": "Other",
                                "exit_uuid": "95afaa0e-a74f-4f3c-9cfb-d64b56e5a35d",
                            },
                        ],
                        "default_category_uuid": "52c54933-7658-4d49-a453-04c3c6541b59",
                        "operand": "@(urn_parts(contact.urn).scheme)",
                        "result_name": "",
                    },
                    "exits": [
                        {
                            "uuid": "ba6d7030-72fe-4e32-8374-b4a81b830851",
                            "destination_uuid": "824f2b51-a07d-4866-bae6-2dfd0ce1e35f",
                        },
                        {
                            "uuid": "95afaa0e-a74f-4f3c-9cfb-d64b56e5a35d",
                            "destination_uuid": "183b5ca1-6a25-40fb-b0cd-8386aa20ae34",
                        },
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
                            "uuid": "2c1ae7ff-6757-4b9b-a7bc-25c48475bef1",
                            "value": "@results.avaliacao.category",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "cdd48623-48db-4836-b4a3-fd32ac276d8a",
                            "uuid": "849c9d3b-213d-45bc-ae8b-d765d3cc048d",
                        }
                    ],
                    "uuid": "24e5fb95-1e1f-4663-ba85-4a735bed09dd",
                },
                {
                    "actions": [],
                    "exits": [
                        {
                            "destination_uuid": None,
                            "uuid": "5c747fe0-56c0-4c8e-8768-2fb8592d4753",
                        },
                        {
                            "destination_uuid": "69d4d33f-bbad-44cc-816c-23a2895ca36b",
                            "uuid": "cc898c6e-b42a-483a-ab5f-ea9dc4859534",
                        },
                    ],
                    "router": {
                        "cases": [
                            {
                                "arguments": ["1"],
                                "category_uuid": "32e69d57-bcd2-4ba5-97ab-bf03fc76974f",
                                "type": "has_any_word",
                                "uuid": "5b9b9847-d50c-4a02-a551-f6fa2cc440d8",
                            }
                        ],
                        "categories": [
                            {
                                "exit_uuid": "5c747fe0-56c0-4c8e-8768-2fb8592d4753",
                                "name": "J\u00e1 tentou 1x",
                                "uuid": "32e69d57-bcd2-4ba5-97ab-bf03fc76974f",
                            },
                            {
                                "exit_uuid": "cc898c6e-b42a-483a-ab5f-ea9dc4859534",
                                "name": "Other",
                                "uuid": "bfe08f1a-75df-4afe-b5ec-81af513ca55e",
                            },
                        ],
                        "default_category_uuid": "bfe08f1a-75df-4afe-b5ec-81af513ca55e",
                        "operand": "@results.tentativa",
                        "type": "switch",
                    },
                    "uuid": "36168769-7912-45dd-9ece-9848ea012e8a",
                },
                {
                    "actions": [
                        {
                            "category": "@results.avaliacao.category",
                            "name": "avaliacao",
                            "type": "set_run_result",
                            "uuid": "aa8c1748-f677-43cb-ae92-310de49914ee",
                            "value": "@results.avaliacao.category",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "97f7d325-128d-42e2-b378-27e7429e4515",
                            "uuid": "9f6bd040-4eb8-48bf-a6fb-ddf267a637d8",
                        }
                    ],
                    "uuid": "cdd48623-48db-4836-b4a3-fd32ac276d8a",
                },
                {
                    "actions": [
                        {
                            "field": {
                                "key": "nota_pesquisa_atendimento_humano",
                                "name": "Nota Pesquisa Atendimento Humano",
                            },
                            "type": "set_contact_field",
                            "uuid": "8eb78165-13b6-4be8-be95-af15a2432891",
                            "value": "@results.avaliacao.category",
                        },
                        {
                            "category": "@results.avaliacao.category",
                            "name": "avaliacao",
                            "type": "set_run_result",
                            "uuid": "2240cb59-cfab-4392-966c-c0275889edc7",
                            "value": "@results.avaliacao.category",
                        },
                    ],
                    "exits": [
                        {
                            "destination_uuid": "795656c5-c260-4711-ad8e-f842b38a01fa",
                            "uuid": "4b81e51b-3a9d-4d42-be48-06b1e1704036",
                        }
                    ],
                    "uuid": "c7008052-12e1-425b-9d83-9ec6d156f9fb",
                },
                {
                    "actions": [
                        {
                            "category": "",
                            "name": "tentativa",
                            "type": "set_run_result",
                            "uuid": "8b862c2d-dfa5-4f7b-a081-3b7d63154085",
                            "value": "@(results.tentativa +1)",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "61459888-cab1-4ac4-9664-61f08756f9cb",
                            "uuid": "184f4279-185b-4cbd-91ad-37eda7415f23",
                        }
                    ],
                    "uuid": "69d4d33f-bbad-44cc-816c-23a2895ca36b",
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
                            "uuid": "bd31a376-db2d-43ab-a0ac-ed7f14246f0c",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "f119a4c1-43dc-42a4-a19d-6875681f32d9",
                            "uuid": "9e1bc2e4-6a34-4259-bd98-a40c819c29e6",
                        },
                        {
                            "destination_uuid": "f119a4c1-43dc-42a4-a19d-6875681f32d9",
                            "uuid": "88198fd7-234e-498b-9a8b-062b56c6128b",
                        },
                    ],
                    "router": {
                        "cases": [
                            {
                                "arguments": ["Success"],
                                "category_uuid": "5c57fe9a-3988-46af-a9b0-b3a384377f17",
                                "type": "has_only_text",
                                "uuid": "9a926ba7-b3d1-4bd1-bc06-37625ff338a6",
                            }
                        ],
                        "categories": [
                            {
                                "exit_uuid": "9e1bc2e4-6a34-4259-bd98-a40c819c29e6",
                                "name": "Success",
                                "uuid": "5c57fe9a-3988-46af-a9b0-b3a384377f17",
                            },
                            {
                                "exit_uuid": "88198fd7-234e-498b-9a8b-062b56c6128b",
                                "name": "Failure",
                                "uuid": "c8f993d7-b1d8-4a94-84be-0687449f8bc3",
                            },
                        ],
                        "default_category_uuid": "c8f993d7-b1d8-4a94-84be-0687449f8bc3",
                        "operand": "@results.result.category",
                        "type": "switch",
                    },
                    "uuid": "97f7d325-128d-42e2-b378-27e7429e4515",
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
                            "uuid": "c0be5385-4f6d-4104-a45c-214ee66dbecb",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "83fd6281-3051-4452-9749-e15dc6bc9f95",
                            "uuid": "79b05645-dc9f-4d70-a0a7-a85f4c601369",
                        },
                        {
                            "destination_uuid": "83fd6281-3051-4452-9749-e15dc6bc9f95",
                            "uuid": "75c208a9-4107-4fae-a4dc-fd93b389d31e",
                        },
                    ],
                    "router": {
                        "cases": [
                            {
                                "arguments": ["Success"],
                                "category_uuid": "68339886-8533-4167-b620-17925eba111e",
                                "type": "has_only_text",
                                "uuid": "9b087e08-b6ab-4e34-8c72-16235e7a41c9",
                            }
                        ],
                        "categories": [
                            {
                                "exit_uuid": "79b05645-dc9f-4d70-a0a7-a85f4c601369",
                                "name": "Success",
                                "uuid": "68339886-8533-4167-b620-17925eba111e",
                            },
                            {
                                "exit_uuid": "75c208a9-4107-4fae-a4dc-fd93b389d31e",
                                "name": "Failure",
                                "uuid": "e7a457b0-7dba-4090-abb6-8e4210304186",
                            },
                        ],
                        "default_category_uuid": "e7a457b0-7dba-4090-abb6-8e4210304186",
                        "operand": "@results.result.category",
                        "type": "switch",
                    },
                    "uuid": "795656c5-c260-4711-ad8e-f842b38a01fa",
                },
                {
                    "actions": [
                        {
                            "attachments": [],
                            "quick_replies": [],
                            "text": "Deixe um coment\u00e1rio sobre sua experi\u00eancia com nosso atendimento \u270d\ufe0f",
                            "type": "send_msg",
                            "uuid": "e7c04b3c-6112-4d12-97f1-0eaafd38c74d",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "a698e8e8-cdba-4a8e-ad88-d3e9c63575a7",
                            "uuid": "d572c29c-fea4-4206-929d-cd55ae41c98b",
                        }
                    ],
                    "uuid": "f119a4c1-43dc-42a4-a19d-6875681f32d9",
                },
                {
                    "actions": [],
                    "exits": [
                        {
                            "destination_uuid": "391f1a65-79aa-4927-8ebd-5f3262e61d20",
                            "uuid": "b51435c3-192f-4f12-8635-fd36ac905c25",
                        },
                        {
                            "destination_uuid": "58d7e185-fa65-40de-b37c-f1a1c112b660",
                            "uuid": "9d486d47-5adb-4e3b-9dd7-7e312d0fdd7e",
                        },
                    ],
                    "router": {
                        "cases": [],
                        "categories": [
                            {
                                "exit_uuid": "b51435c3-192f-4f12-8635-fd36ac905c25",
                                "name": "All Responses",
                                "uuid": "3b43c6bb-4b8b-447e-9c6c-41b7a20e4cc4",
                            },
                            {
                                "exit_uuid": "9d486d47-5adb-4e3b-9dd7-7e312d0fdd7e",
                                "name": "No Response",
                                "uuid": "bf5bd4c4-667d-4f33-89df-9fbbc21d63c9",
                            },
                        ],
                        "default_category_uuid": "3b43c6bb-4b8b-447e-9c6c-41b7a20e4cc4",
                        "operand": "@input.text",
                        "result_name": "comentario",
                        "type": "switch",
                        "wait": {
                            "timeout": {
                                "category_uuid": "bf5bd4c4-667d-4f33-89df-9fbbc21d63c9",
                                "seconds": 600,
                            },
                            "type": "msg",
                        },
                    },
                    "uuid": "a698e8e8-cdba-4a8e-ad88-d3e9c63575a7",
                },
                {
                    "actions": [
                        {
                            "attachments": [],
                            "quick_replies": [],
                            "text": "Deixe um coment\u00e1rio para sempre melhorarmos nosso atendimento \u270d\ufe0f",
                            "type": "send_msg",
                            "uuid": "b62f8f9b-4b10-4db9-80f1-90a1a43d97e8",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "8ead47fc-6ace-487d-8268-9c658abdeade",
                            "uuid": "7e2c2628-b4f8-4512-b851-9ce9c18f5d0d",
                        }
                    ],
                    "uuid": "83fd6281-3051-4452-9749-e15dc6bc9f95",
                },
                {
                    "actions": [],
                    "exits": [
                        {
                            "destination_uuid": "fca21cac-795d-42a6-9bc3-daa140fee450",
                            "uuid": "cb1e20fc-04a8-49c9-9c02-c7ed59d9d297",
                        },
                        {
                            "destination_uuid": "09212661-8055-4bdf-ae23-3d3b6667632f",
                            "uuid": "7f6eca55-3fd2-4f51-8663-d74f8f35614d",
                        },
                    ],
                    "router": {
                        "cases": [],
                        "categories": [
                            {
                                "exit_uuid": "cb1e20fc-04a8-49c9-9c02-c7ed59d9d297",
                                "name": "All Responses",
                                "uuid": "7861d8d3-1bf4-4e2f-92c6-a1d583c12326",
                            },
                            {
                                "exit_uuid": "7f6eca55-3fd2-4f51-8663-d74f8f35614d",
                                "name": "No Response",
                                "uuid": "42add051-0a5b-4760-bcbf-92e34677b4be",
                            },
                        ],
                        "default_category_uuid": "7861d8d3-1bf4-4e2f-92c6-a1d583c12326",
                        "operand": "@input.text",
                        "result_name": "comentario",
                        "type": "switch",
                        "wait": {
                            "timeout": {
                                "category_uuid": "42add051-0a5b-4760-bcbf-92e34677b4be",
                                "seconds": 600,
                            },
                            "type": "msg",
                        },
                    },
                    "uuid": "8ead47fc-6ace-487d-8268-9c658abdeade",
                },
                {
                    "actions": [
                        {
                            "attachments": [],
                            "quick_replies": [],
                            "text": "Seu atendimento foi finalizado.\n\nAgradecemos a sua colabora\u00e7\u00e3o. At\u00e9 a pr\u00f3xima \ud83d\udc4b",
                            "type": "send_msg",
                            "uuid": "58c3086c-2936-46e5-8fd5-498c47cccc05",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "9f3b308e-478c-4921-88b4-e72f737db459",
                            "uuid": "6ee2af0b-01fa-4f03-8e50-98571fd5487f",
                        }
                    ],
                    "uuid": "391f1a65-79aa-4927-8ebd-5f3262e61d20",
                },
                {
                    "actions": [
                        {
                            "category": "N\u00e3o respondente",
                            "name": "comentario",
                            "type": "set_run_result",
                            "uuid": "2bbfab2c-4c50-427d-b7fd-594ad8c97c38",
                            "value": "N\u00e3o respondente",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "9f3b308e-478c-4921-88b4-e72f737db459",
                            "uuid": "470d51b6-73ff-431b-bfc5-5e57766fbff8",
                        }
                    ],
                    "uuid": "58d7e185-fa65-40de-b37c-f1a1c112b660",
                },
                {
                    "actions": [
                        {
                            "attachments": [],
                            "quick_replies": [],
                            "text": "Seu atendimento foi finalizado. Iremos analisar seu coment\u00e1rio com responsabilidade. \n\nAgradecemos a sua colabora\u00e7\u00e3o para melhorar o atendimento. At\u00e9 a pr\u00f3xima \ud83d\udc4b",
                            "type": "send_msg",
                            "uuid": "71880b13-5e44-4626-91af-0f52a549ae47",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "9f3b308e-478c-4921-88b4-e72f737db459",
                            "uuid": "8c07f4db-f422-4942-aeea-3ee68f84cefc",
                        }
                    ],
                    "uuid": "fca21cac-795d-42a6-9bc3-daa140fee450",
                },
                {
                    "actions": [
                        {
                            "category": "N\u00e3o respondente",
                            "name": "comentario",
                            "type": "set_run_result",
                            "uuid": "0d818fcd-d822-4e37-a037-e43ea4f77612",
                            "value": "N\u00e3o respondente",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "9f3b308e-478c-4921-88b4-e72f737db459",
                            "uuid": "4431a5cc-9ebf-41b4-a298-79cf818c473f",
                        }
                    ],
                    "uuid": "09212661-8055-4bdf-ae23-3d3b6667632f",
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
                            "uuid": "ad9d7fd3-9dba-4e7b-b2b9-fff18309907e",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": None,
                            "uuid": "5077a670-28cb-4193-80cb-3c360088e63f",
                        },
                        {
                            "destination_uuid": None,
                            "uuid": "c5e48b2c-a06b-405a-b10f-717dcede8167",
                        },
                    ],
                    "router": {
                        "cases": [
                            {
                                "arguments": ["Success"],
                                "category_uuid": "2b5cd176-1248-4d55-a334-8ee42b604772",
                                "type": "has_only_text",
                                "uuid": "d88870c2-a0eb-4a53-876e-8f995c09bbb8",
                            }
                        ],
                        "categories": [
                            {
                                "exit_uuid": "5077a670-28cb-4193-80cb-3c360088e63f",
                                "name": "Success",
                                "uuid": "2b5cd176-1248-4d55-a334-8ee42b604772",
                            },
                            {
                                "exit_uuid": "c5e48b2c-a06b-405a-b10f-717dcede8167",
                                "name": "Failure",
                                "uuid": "d202a37e-d816-4a78-8bd5-463a840876d9",
                            },
                        ],
                        "default_category_uuid": "d202a37e-d816-4a78-8bd5-463a840876d9",
                        "operand": "@results.result.category",
                        "type": "switch",
                    },
                    "uuid": "9f3b308e-478c-4921-88b4-e72f737db459",
                },
            ],
            "spec_version": "13.1.0",
            "type": "messaging",
            "uuid": "f75f5c12-b97f-4ab8-91c3-2b7a5a2cd0c1",
            "revision": 86,
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
