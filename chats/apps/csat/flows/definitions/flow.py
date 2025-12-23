# This is a placeholder and will be changed later to the actual flow definition

CSAT_FLOW_VERSION = 1
CSAT_FLOW_NAME = "Weni Chats CSAT Flow"
CSAT_FLOW_DEFINITION_DATA = {
    "version": "13",
    "site": "https://flows.weni.ai",
    "flows": [
        {
            "_ui": {
                "nodes": {
                    "2e1f850e-3f6e-4871-9397-bc203150dee5": {
                        "position": {
                            "left": "1342.074049511356",
                            "top": "1254.275597947668",
                        },
                        "type": "execute_actions",
                    },
                    "b9ebab44-c128-481b-8954-f4c85015c817": {
                        "config": {"cases": {}},
                        "position": {
                            "left": "1344.7429126871152",
                            "top": "1454.653596440618",
                        },
                        "type": "split_by_scheme",
                    },
                    "4cd80fe0-94b1-4926-b0f8-4838aa74a75d": {
                        "position": {
                            "left": "1135.002130439344",
                            "top": "1644.0453112453636",
                        },
                        "type": "execute_actions",
                    },
                    "b020f657-9f36-481e-9d6d-f8f4f1ea1cec": {
                        "position": {
                            "left": "1537.7174976978713",
                            "top": "1645.4129353706592",
                        },
                        "type": "execute_actions",
                    },
                    "ba69ec44-a454-4040-9ceb-6034a4062471": {
                        "position": {
                            "left": "2102.730635385634",
                            "top": "1864.5697418429131",
                        },
                        "type": "execute_actions",
                    },
                    "fa05fd8d-b48d-4efa-83be-bf5909e17a5e": {
                        "type": "wait_for_response",
                        "position": {
                            "left": "1157.2408609900526",
                            "top": "2031.653596440618",
                        },
                        "config": {"cases": {}},
                    },
                    "e44d55c1-dc42-4d79-80d2-f6f99a81921e": {
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
                    "0d552af3-2d5e-4d82-a371-ea1630682cd6": {
                        "position": {
                            "left": "530.5389376101214",
                            "top": "2304.638408866735",
                        },
                        "type": "execute_actions",
                    },
                    "3c5eb7ee-2ca9-4ef1-a0ce-3d3aeaa4caee": {
                        "position": {
                            "left": "1211.8007743109872",
                            "top": "2354.7407051418536",
                        },
                        "type": "execute_actions",
                    },
                    "b7205ca8-332b-491b-828d-977f926da067": {
                        "position": {
                            "left": "532.1525515926652",
                            "top": "2484.2901920528925",
                        },
                        "type": "execute_actions",
                    },
                    "b573a778-ceba-419b-b90c-648c67d01cdd": {
                        "position": {
                            "left": "1212.9127841724944",
                            "top": "2744.0731410222365",
                        },
                        "type": "execute_actions",
                    },
                    "8ed3fdc1-52b6-4c94-ac8c-90a81f5de661": {
                        "position": {
                            "left": "534.7028958280318",
                            "top": "2777.623525386226",
                        },
                        "type": "execute_actions",
                    },
                    "947040c4-66ec-4cb8-9193-72277bf5a817": {
                        "position": {
                            "left": "1216.6290399328577",
                            "top": "2946.571929565236",
                        },
                        "type": "execute_actions",
                    },
                    "35c6a45b-cacb-4949-8e00-e0227cd49c77": {
                        "config": {"cases": {}},
                        "position": {
                            "left": "531.4199459661597",
                            "top": "2986.3440877475277",
                        },
                        "type": "wait_for_response",
                    },
                    "b6e40dc7-c7a3-4c72-b417-e1c8bf8867da": {
                        "config": {"cases": {}},
                        "position": {
                            "left": "1211.3460900709856",
                            "top": "3197.571929565236",
                        },
                        "type": "wait_for_response",
                    },
                    "a69bba98-4c15-44f3-bd68-f5d8b62093f5": {
                        "position": {
                            "left": "535.4199459661597",
                            "top": "3219.3440877475277",
                        },
                        "type": "execute_actions",
                    },
                    "0fc2dae0-49c7-4e09-9b6a-e4be0887088f": {
                        "position": {
                            "left": "796.927464564468",
                            "top": "3224.6395402223325",
                        },
                        "type": "execute_actions",
                    },
                    "82fa6589-e918-455d-a6f9-cd0ccda9142f": {
                        "position": {
                            "left": "1215.3460900709856",
                            "top": "3401.4251190743635",
                        },
                        "type": "execute_actions",
                    },
                    "11a0c6d8-3752-4478-b7e0-79a96c98c244": {
                        "position": {
                            "left": "1479.7303603839714",
                            "top": "3403.84381983449",
                        },
                        "type": "execute_actions",
                    },
                    "dd2320a5-4001-41ca-9460-fc80dc96e1ef": {
                        "type": "split_by_webhook",
                        "position": {
                            "left": "908.7015043077097",
                            "top": "3790.3354566551607",
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
                    "f4f08916-f4d9-463a-8a5f-fca41b3e1464": {
                        "text": [
                            "Before we go, tell us about your experience!\n*How would you rate my service?* \ud83d\udc47"
                        ],
                        "quick_replies": [],
                        "header_text": ["Customer Satisfaction Survey"],
                        "footer": [
                            "It\u2019s very quick, it won\u2019t even take a minute."
                        ],
                        "button_text": ["Select here"],
                    },
                    "d66e53f8-2678-4719-a488-631faea30f04": {
                        "title": ["Very dissatisfied \ud83d\ude23"],
                        "description": [""],
                    },
                    "53f8bbd9-9bd9-4503-a0b9-cfd347600e79": {
                        "title": ["Dissatisfied \ud83d\ude41"],
                        "description": [""],
                    },
                    "f4c64614-2912-41af-8ebc-7101186c9e29": {
                        "title": ["Neutral \ud83d\ude36"],
                        "description": [""],
                    },
                    "ee120af4-7e6a-4eef-bbe8-ca021f9063d2": {
                        "title": ["Satisfied \ud83d\ude42"],
                        "description": [""],
                    },
                    "029b4fd0-dc7d-4022-9a63-0fa0a5fe0a12": {
                        "title": ["Very satisfied \ud83d\ude03"],
                        "description": [""],
                    },
                    "5c1cb2ab-e3ef-4a6c-8f2d-8ecbf17f004f": {
                        "arguments": ["Very satisfied \ud83d\ude03"]
                    },
                    "222385f3-ca43-4913-8c62-ec15852d8021": {
                        "arguments": ["Satisfied \ud83d\ude42"]
                    },
                    "d719b03c-4f71-44fb-bcd6-7bea8b80d0f0": {
                        "arguments": ["Neutral \ud83d\ude36"]
                    },
                    "f9ace0f0-faac-4320-9974-5f3b182c5481": {
                        "arguments": ["Dissatisfied \ud83d\ude41"]
                    },
                    "bf9eb137-f853-4154-92ec-f428f8cef32d": {
                        "arguments": ["Very dissatisfied \ud83d\ude23"]
                    },
                    "9f974669-1450-4c4a-b076-a60c37236ee2": {"arguments": ["great"]},
                    "e2c5ee4f-1b8c-43e3-af1b-96448b4005d9": {"arguments": ["good"]},
                    "6e0bdb7e-abb8-434c-abee-1e7c036d71f1": {
                        "arguments": ["neutral normal ok"]
                    },
                    "120bd83a-bb64-4fc0-8b55-6e2ae6413529": {"arguments": ["bad poor"]},
                    "03e04c3a-ee57-4604-b542-7b04227f3afb": {
                        "arguments": ["terrible horrible"]
                    },
                    "43f281be-01ae-4da8-bae6-bb49b07f35fb": {
                        "arguments": ["satisfied"]
                    },
                    "f21315b6-4d99-45df-9b38-46ca67d6fb13": {
                        "text": [
                            "Before we go, tell us about your experience!\n\n**How would you rate my service?** \ud83d\udc47"
                        ],
                        "attachments": [],
                        "quick_replies": [
                            "Very dissatisfied \ud83d\ude23",
                            "Dissatisfied \ud83d\ude41",
                            "Neutral \ud83d\ude36",
                            "Satisfied \ud83d\ude42",
                            "Very satisfied \ud83d\ude03",
                        ],
                    },
                    "e00688d1-7c85-43de-9ae9-4c381bd732dc": {
                        "text": [
                            "Before continuing, could you please answer our survey below?"
                        ],
                        "attachments": [],
                    },
                    "b6eeb06b-5e7f-4df4-b857-2f59f2d39a37": {
                        "text": [
                            "Leave a comment about your experience with our service \u270d\ufe0f"
                        ],
                        "attachments": [],
                    },
                    "898136db-4601-4f9f-a133-c323581e9dc2": {
                        "text": [
                            "Leave a comment so we can keep improving our service \u270d\ufe0f"
                        ],
                        "attachments": [],
                    },
                    "246fff75-bb2d-469e-8394-2900cdbe6d84": {
                        "text": [
                            "Your session has ended.\n\nThank you for your feedback. See you next time! \ud83d\udc4b"
                        ],
                        "attachments": [],
                    },
                    "4d2bd028-62d2-454b-a9d4-0b2e3e4c1cc4": {
                        "text": [
                            "Your session has ended. We will carefully review your feedback.\n\nThank you for helping us improve our service. See you next time! \ud83d\udc4b"
                        ],
                        "attachments": [],
                    },
                },
                "spa": {
                    "f4f08916-f4d9-463a-8a5f-fca41b3e1464": {
                        "text": [
                            "Antes de terminar, \u00a1cu\u00e9ntanos tu experiencia!\n*\u00bfC\u00f3mo valoras mi atenci\u00f3n?* \ud83d\udc47"
                        ],
                        "quick_replies": [],
                        "header_text": ["Encuesta de Satisfacci\u00f3n"],
                        "footer": [
                            "Es muy r\u00e1pido, no te quitar\u00e1 ni un minuto."
                        ],
                        "button_text": ["Selecciona aqu\u00ed"],
                    },
                    "d66e53f8-2678-4719-a488-631faea30f04": {
                        "title": ["Muy insatisfecho \ud83d\ude23"],
                        "description": [""],
                    },
                    "53f8bbd9-9bd9-4503-a0b9-cfd347600e79": {
                        "title": ["Insatisfecho \ud83d\ude41"],
                        "description": [""],
                    },
                    "f4c64614-2912-41af-8ebc-7101186c9e29": {
                        "title": ["Neutral \ud83d\ude36"],
                        "description": [""],
                    },
                    "ee120af4-7e6a-4eef-bbe8-ca021f9063d2": {
                        "title": ["Satisfecho \ud83d\ude42"],
                        "description": [""],
                    },
                    "029b4fd0-dc7d-4022-9a63-0fa0a5fe0a12": {
                        "title": ["Muy satisfecho \ud83d\ude03"],
                        "description": [""],
                    },
                    "f21315b6-4d99-45df-9b38-46ca67d6fb13": {
                        "text": [
                            "Antes de terminar, \u00a1cu\u00e9ntanos tu experiencia!\n\n**\u00bfC\u00f3mo valoras mi atenci\u00f3n?** \ud83d\udc47"
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
                    "5c1cb2ab-e3ef-4a6c-8f2d-8ecbf17f004f": {
                        "arguments": ["Muy satisfecho \ud83d\ude03"]
                    },
                    "222385f3-ca43-4913-8c62-ec15852d8021": {
                        "arguments": ["Satisfecho \ud83d\ude42"]
                    },
                    "d719b03c-4f71-44fb-bcd6-7bea8b80d0f0": {
                        "arguments": ["Neutral \ud83d\ude36"]
                    },
                    "f9ace0f0-faac-4320-9974-5f3b182c5481": {
                        "arguments": ["Insatisfecho \ud83d\ude41"]
                    },
                    "bf9eb137-f853-4154-92ec-f428f8cef32d": {
                        "arguments": ["Muy insatisfecho \ud83d\ude23"]
                    },
                    "9f974669-1450-4c4a-b076-a60c37236ee2": {
                        "arguments": ["excelente"]
                    },
                    "e2c5ee4f-1b8c-43e3-af1b-96448b4005d9": {
                        "arguments": ["bueno buena"]
                    },
                    "6e0bdb7e-abb8-434c-abee-1e7c036d71f1": {
                        "arguments": ["normal neutral"]
                    },
                    "120bd83a-bb64-4fc0-8b55-6e2ae6413529": {
                        "arguments": ["malo mala"]
                    },
                    "03e04c3a-ee57-4604-b542-7b04227f3afb": {
                        "arguments": ["horrible terrible"]
                    },
                    "43f281be-01ae-4da8-bae6-bb49b07f35fb": {
                        "arguments": ["satisfecho satisfecha"]
                    },
                    "b6eeb06b-5e7f-4df4-b857-2f59f2d39a37": {
                        "text": [
                            "D\u00e9janos un comentario sobre tu experiencia con nuestra atenci\u00f3n \u270d\ufe0f"
                        ],
                        "attachments": [],
                    },
                    "898136db-4601-4f9f-a133-c323581e9dc2": {
                        "text": [
                            "D\u00e9janos un comentario para que podamos seguir mejorando nuestra atenci\u00f3n \u270d\ufe0f"
                        ],
                        "attachments": [],
                    },
                    "246fff75-bb2d-469e-8394-2900cdbe6d84": {
                        "text": [
                            "Tu atenci\u00f3n ha finalizado.\n\nAgradecemos tu colaboraci\u00f3n. \u00a1Hasta la pr\u00f3xima! \ud83d\udc4b"
                        ],
                        "attachments": [],
                    },
                    "4d2bd028-62d2-454b-a9d4-0b2e3e4c1cc4": {
                        "text": [
                            "Tu atenci\u00f3n ha finalizado. Analizaremos tu comentario con responsabilidad.\n\nGracias por ayudarnos a mejorar nuestra atenci\u00f3n. \u00a1Hasta la pr\u00f3xima! \ud83d\udc4b"
                        ],
                        "attachments": [],
                    },
                    "e00688d1-7c85-43de-9ae9-4c381bd732dc": {
                        "text": [
                            "Antes de continuar, \u00bfpodr\u00edas responder a nuestra encuesta de abajo?"
                        ],
                        "attachments": [],
                    },
                },
                "por": {
                    "f4f08916-f4d9-463a-8a5f-fca41b3e1464": {
                        "text": [
                            "Antes de encerrar, conte como foi sua experi\u00eancia!\n*Como voc\u00ea avalia o meu atendimento?* \ud83d\udc47"
                        ],
                        "quick_replies": [],
                        "header_text": ["Pesquisa de Satisfa\u00e7\u00e3o"],
                        "footer": [
                            "\u00c9 bem r\u00e1pido, n\u00e3o vai demorar nem 1 minuto."
                        ],
                        "button_text": ["Selecione aqui"],
                    },
                    "d66e53f8-2678-4719-a488-631faea30f04": {
                        "title": ["Muito insatisfeito \ud83d\ude23"],
                        "description": [""],
                    },
                    "53f8bbd9-9bd9-4503-a0b9-cfd347600e79": {
                        "title": ["Insatisfeito \ud83d\ude41"],
                        "description": [""],
                    },
                    "f4c64614-2912-41af-8ebc-7101186c9e29": {
                        "title": ["Neutro \ud83d\ude36"],
                        "description": [""],
                    },
                    "ee120af4-7e6a-4eef-bbe8-ca021f9063d2": {
                        "title": ["Satisfeito \ud83d\ude42"],
                        "description": [""],
                    },
                    "029b4fd0-dc7d-4022-9a63-0fa0a5fe0a12": {
                        "title": ["Muito satisfeito \ud83d\ude03"],
                        "description": [""],
                    },
                    "f21315b6-4d99-45df-9b38-46ca67d6fb13": {
                        "text": [
                            "Antes de encerrar, conte como foi sua experi\u00eancia!\n\n**Como voc\u00ea avalia o meu atendimento?** \ud83d\udc47"
                        ],
                        "attachments": [],
                    },
                    "e00688d1-7c85-43de-9ae9-4c381bd732dc": {
                        "text": [
                            "Antes de continuar, poderia responder nossa pesquisa abaixo?"
                        ],
                        "attachments": [],
                    },
                    "b6eeb06b-5e7f-4df4-b857-2f59f2d39a37": {
                        "text": [
                            "Deixe um coment\u00e1rio sobre sua experi\u00eancia com nosso atendimento \u270d\ufe0f"
                        ],
                        "attachments": [],
                    },
                    "898136db-4601-4f9f-a133-c323581e9dc2": {
                        "text": [
                            "Deixe um coment\u00e1rio para sempre melhorarmos nosso atendimento \u270d\ufe0f"
                        ],
                        "attachments": [],
                    },
                    "246fff75-bb2d-469e-8394-2900cdbe6d84": {
                        "text": [
                            "Seu atendimento foi finalizado.\n\nAgradecemos a sua colabora\u00e7\u00e3o. At\u00e9 a pr\u00f3xima \ud83d\udc4b"
                        ],
                        "attachments": [],
                    },
                    "4d2bd028-62d2-454b-a9d4-0b2e3e4c1cc4": {
                        "text": [
                            "Seu atendimento foi finalizado. Iremos analisar seu coment\u00e1rio com responsabilidade.\n\nAgradecemos a sua colabora\u00e7\u00e3o para melhorar o atendimento. At\u00e9 a pr\u00f3xima \ud83d\udc4b"
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
                            "uuid": "dc71ab5b-cc86-4a1f-863d-0a658b2c0f3c",
                            "value": "0",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "b9ebab44-c128-481b-8954-f4c85015c817",
                            "uuid": "bcede528-7d80-4178-a8da-d3cbdb299b0e",
                        }
                    ],
                    "uuid": "2e1f850e-3f6e-4871-9397-bc203150dee5",
                },
                {
                    "actions": [],
                    "exits": [
                        {
                            "destination_uuid": "4cd80fe0-94b1-4926-b0f8-4838aa74a75d",
                            "uuid": "0733237c-97cc-490a-a6d2-b78df94de026",
                        },
                        {
                            "destination_uuid": "b020f657-9f36-481e-9d6d-f8f4f1ea1cec",
                            "uuid": "7f7cc7b8-901a-4a88-9e16-8ed90abbca38",
                        },
                    ],
                    "router": {
                        "cases": [
                            {
                                "arguments": ["whatsapp"],
                                "category_uuid": "60ee929c-cc03-40b8-8742-5fd5c96eab19",
                                "type": "has_only_phrase",
                                "uuid": "d1d07268-fed3-49ff-98df-608346aa2b6b",
                            }
                        ],
                        "categories": [
                            {
                                "exit_uuid": "0733237c-97cc-490a-a6d2-b78df94de026",
                                "name": "WhatsApp",
                                "uuid": "60ee929c-cc03-40b8-8742-5fd5c96eab19",
                            },
                            {
                                "exit_uuid": "7f7cc7b8-901a-4a88-9e16-8ed90abbca38",
                                "name": "Other",
                                "uuid": "dd68f4fb-452b-4b24-bace-46ba7dbd9e7b",
                            },
                        ],
                        "default_category_uuid": "dd68f4fb-452b-4b24-bace-46ba7dbd9e7b",
                        "operand": "@(urn_parts(contact.urn).scheme)",
                        "result_name": "",
                        "type": "switch",
                    },
                    "uuid": "b9ebab44-c128-481b-8954-f4c85015c817",
                },
                {
                    "actions": [
                        {
                            "type": "send_whatsapp_msg",
                            "text": "Antes de encerrar, conte como foi sua experi\u00eancia!\n*Como voc\u00ea avalia o meu atendimento?* \ud83d\udc47",
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
                                    "uuid": "d66e53f8-2678-4719-a488-631faea30f04",
                                },
                                {
                                    "description": "",
                                    "title": "Insatisfeito \ud83d\ude41",
                                    "uuid": "53f8bbd9-9bd9-4503-a0b9-cfd347600e79",
                                },
                                {
                                    "description": "",
                                    "title": "Neutro \ud83d\ude36",
                                    "uuid": "f4c64614-2912-41af-8ebc-7101186c9e29",
                                },
                                {
                                    "description": "",
                                    "title": "Satisfeito \ud83d\ude42",
                                    "uuid": "ee120af4-7e6a-4eef-bbe8-ca021f9063d2",
                                },
                                {
                                    "description": "",
                                    "title": "Muito satisfeito \ud83d\ude03",
                                    "uuid": "029b4fd0-dc7d-4022-9a63-0fa0a5fe0a12",
                                },
                            ],
                            "uuid": "f4f08916-f4d9-463a-8a5f-fca41b3e1464",
                            "flow_data_attachment_name_map": {},
                            "quick_replies": [],
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "fa05fd8d-b48d-4efa-83be-bf5909e17a5e",
                            "uuid": "8ffc1371-8a5e-4b3b-ae4c-071667b67585",
                        }
                    ],
                    "uuid": "4cd80fe0-94b1-4926-b0f8-4838aa74a75d",
                },
                {
                    "actions": [
                        {
                            "attachments": [],
                            "text": "Antes de encerrar, conte como foi sua experi\u00eancia!\n\n**Como voc\u00ea avalia o meu atendimento?** \ud83d\udc47",
                            "type": "send_msg",
                            "quick_replies": [
                                "Muito insatisfeito \ud83d\ude23",
                                "Insatisfeito \ud83d\ude41",
                                "Neutro \ud83d\ude36",
                                "Satisfeito \ud83d\ude42",
                                "Muito satisfeito \ud83d\ude03",
                            ],
                            "uuid": "f21315b6-4d99-45df-9b38-46ca67d6fb13",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "fa05fd8d-b48d-4efa-83be-bf5909e17a5e",
                            "uuid": "5264236c-2c78-4a99-9e73-e40955e5f3cb",
                        }
                    ],
                    "uuid": "b020f657-9f36-481e-9d6d-f8f4f1ea1cec",
                },
                {
                    "actions": [
                        {
                            "attachments": [],
                            "quick_replies": [],
                            "text": "Antes de continuar, poderia responder nossa pesquisa abaixo?",
                            "type": "send_msg",
                            "uuid": "e00688d1-7c85-43de-9ae9-4c381bd732dc",
                        },
                        {
                            "category": "",
                            "name": "tentativa",
                            "type": "set_run_result",
                            "uuid": "6ffb6cf9-0537-4bd2-97f4-d417e2c3c6ed",
                            "value": "@(results.tentativa +1)",
                        },
                    ],
                    "exits": [
                        {
                            "destination_uuid": "b9ebab44-c128-481b-8954-f4c85015c817",
                            "uuid": "563f0361-3cd3-48b1-836e-a63210184c4a",
                        }
                    ],
                    "uuid": "ba69ec44-a454-4040-9ceb-6034a4062471",
                },
                {
                    "uuid": "fa05fd8d-b48d-4efa-83be-bf5909e17a5e",
                    "actions": [],
                    "router": {
                        "type": "switch",
                        "default_category_uuid": "cb36c75e-7811-4dad-9f6a-3d13ca387ede",
                        "cases": [
                            {
                                "arguments": ["Muito satisfeito \ud83d\ude03"],
                                "type": "has_only_phrase",
                                "uuid": "5c1cb2ab-e3ef-4a6c-8f2d-8ecbf17f004f",
                                "category_uuid": "bf41eee7-71d9-4359-927f-b4d8aedb4cc3",
                            },
                            {
                                "arguments": ["Satisfeito \ud83d\ude42"],
                                "type": "has_only_phrase",
                                "uuid": "222385f3-ca43-4913-8c62-ec15852d8021",
                                "category_uuid": "c1c962a9-e13f-4032-99fa-422521be304a",
                            },
                            {
                                "arguments": ["Neutro \ud83d\ude36"],
                                "type": "has_only_phrase",
                                "uuid": "d719b03c-4f71-44fb-bcd6-7bea8b80d0f0",
                                "category_uuid": "0177d24c-f2de-4187-99f9-b17b76228eb5",
                            },
                            {
                                "arguments": ["Insatisfeito \ud83d\ude41"],
                                "type": "has_only_phrase",
                                "uuid": "f9ace0f0-faac-4320-9974-5f3b182c5481",
                                "category_uuid": "4c292a48-6c1b-4e47-92df-e30e60d3c085",
                            },
                            {
                                "arguments": ["Muito insatisfeito \ud83d\ude23"],
                                "type": "has_only_phrase",
                                "uuid": "bf9eb137-f853-4154-92ec-f428f8cef32d",
                                "category_uuid": "19dcf48a-2dd1-4e91-b1da-4e1a92c49ce0",
                            },
                            {
                                "arguments": ["\u00f3timo otimo"],
                                "type": "has_any_word",
                                "uuid": "9f974669-1450-4c4a-b076-a60c37236ee2",
                                "category_uuid": "bf41eee7-71d9-4359-927f-b4d8aedb4cc3",
                            },
                            {
                                "arguments": ["bom boa"],
                                "type": "has_any_word",
                                "uuid": "e2c5ee4f-1b8c-43e3-af1b-96448b4005d9",
                                "category_uuid": "c1c962a9-e13f-4032-99fa-422521be304a",
                            },
                            {
                                "arguments": ["neutro neutra normal"],
                                "type": "has_any_word",
                                "uuid": "6e0bdb7e-abb8-434c-abee-1e7c036d71f1",
                                "category_uuid": "0177d24c-f2de-4187-99f9-b17b76228eb5",
                            },
                            {
                                "arguments": ["ruim rum"],
                                "type": "has_any_word",
                                "uuid": "120bd83a-bb64-4fc0-8b55-6e2ae6413529",
                                "category_uuid": "4c292a48-6c1b-4e47-92df-e30e60d3c085",
                            },
                            {
                                "arguments": ["p\u00e9ssimo pessimo pesimo"],
                                "type": "has_any_word",
                                "uuid": "03e04c3a-ee57-4604-b542-7b04227f3afb",
                                "category_uuid": "19dcf48a-2dd1-4e91-b1da-4e1a92c49ce0",
                            },
                            {
                                "arguments": ["satisfeito satisfeita"],
                                "type": "has_any_word",
                                "uuid": "43f281be-01ae-4da8-bae6-bb49b07f35fb",
                                "category_uuid": "c1c962a9-e13f-4032-99fa-422521be304a",
                            },
                        ],
                        "categories": [
                            {
                                "exit_uuid": "6af21211-97c5-4952-8413-daff967fc9e4",
                                "name": "5",
                                "uuid": "bf41eee7-71d9-4359-927f-b4d8aedb4cc3",
                            },
                            {
                                "exit_uuid": "67d52193-2707-4ad4-88fb-28cced29aed0",
                                "name": "4",
                                "uuid": "c1c962a9-e13f-4032-99fa-422521be304a",
                            },
                            {
                                "exit_uuid": "b8afa9b9-0733-4e2e-983c-2752b795f6df",
                                "name": "3",
                                "uuid": "0177d24c-f2de-4187-99f9-b17b76228eb5",
                            },
                            {
                                "exit_uuid": "17b56bef-c464-4ce6-a55e-7e8dd80a484c",
                                "name": "2",
                                "uuid": "4c292a48-6c1b-4e47-92df-e30e60d3c085",
                            },
                            {
                                "exit_uuid": "387f816b-909d-4ca0-8180-b1c6d7812ac9",
                                "name": "1",
                                "uuid": "19dcf48a-2dd1-4e91-b1da-4e1a92c49ce0",
                            },
                            {
                                "exit_uuid": "3f8d729d-0718-483a-ab81-da0a0723c9f1",
                                "name": "Other",
                                "uuid": "cb36c75e-7811-4dad-9f6a-3d13ca387ede",
                            },
                            {
                                "exit_uuid": "9a99e3c0-c235-46fa-bc10-fdf239789fbe",
                                "name": "No Response",
                                "uuid": "737b3a02-abb2-4f51-82b0-46eaeccbfc10",
                            },
                        ],
                        "operand": "@input.text",
                        "wait": {
                            "type": "msg",
                            "timeout": {
                                "seconds": 3600,
                                "category_uuid": "737b3a02-abb2-4f51-82b0-46eaeccbfc10",
                            },
                        },
                        "result_name": "avaliacao",
                    },
                    "exits": [
                        {
                            "destination_uuid": "0d552af3-2d5e-4d82-a371-ea1630682cd6",
                            "uuid": "6af21211-97c5-4952-8413-daff967fc9e4",
                        },
                        {
                            "destination_uuid": "0d552af3-2d5e-4d82-a371-ea1630682cd6",
                            "uuid": "67d52193-2707-4ad4-88fb-28cced29aed0",
                        },
                        {
                            "destination_uuid": "3c5eb7ee-2ca9-4ef1-a0ce-3d3aeaa4caee",
                            "uuid": "b8afa9b9-0733-4e2e-983c-2752b795f6df",
                        },
                        {
                            "destination_uuid": "b573a778-ceba-419b-b90c-648c67d01cdd",
                            "uuid": "17b56bef-c464-4ce6-a55e-7e8dd80a484c",
                        },
                        {
                            "destination_uuid": "b573a778-ceba-419b-b90c-648c67d01cdd",
                            "uuid": "387f816b-909d-4ca0-8180-b1c6d7812ac9",
                        },
                        {
                            "destination_uuid": "e44d55c1-dc42-4d79-80d2-f6f99a81921e",
                            "uuid": "3f8d729d-0718-483a-ab81-da0a0723c9f1",
                        },
                        {"uuid": "9a99e3c0-c235-46fa-bc10-fdf239789fbe"},
                    ],
                },
                {
                    "actions": [],
                    "exits": [
                        {
                            "destination_uuid": None,
                            "uuid": "643596ae-f40f-4a95-a4c9-66f299c86cf1",
                        },
                        {
                            "destination_uuid": "ba69ec44-a454-4040-9ceb-6034a4062471",
                            "uuid": "eeece6fc-05c0-4c25-8abf-58e22d7bbd7c",
                        },
                    ],
                    "router": {
                        "cases": [
                            {
                                "arguments": ["1"],
                                "category_uuid": "049e60a3-04da-4821-ad42-9dcfbed8a84d",
                                "type": "has_any_word",
                                "uuid": "30452f82-3ce5-48f7-95b6-51357888c558",
                            }
                        ],
                        "categories": [
                            {
                                "exit_uuid": "643596ae-f40f-4a95-a4c9-66f299c86cf1",
                                "name": "J\u00e1 tentou 1x",
                                "uuid": "049e60a3-04da-4821-ad42-9dcfbed8a84d",
                            },
                            {
                                "exit_uuid": "eeece6fc-05c0-4c25-8abf-58e22d7bbd7c",
                                "name": "Other",
                                "uuid": "8076f6bc-44dd-491a-a46d-2508b441e27f",
                            },
                        ],
                        "default_category_uuid": "8076f6bc-44dd-491a-a46d-2508b441e27f",
                        "operand": "@results.tentativa",
                        "type": "switch",
                    },
                    "uuid": "e44d55c1-dc42-4d79-80d2-f6f99a81921e",
                },
                {
                    "actions": [
                        {
                            "field": {
                                "key": "nota_pesquisa_atendimento_humano",
                                "name": "Nota Pesquisa Atendimento Humano",
                            },
                            "type": "set_contact_field",
                            "uuid": "d7a5419d-407e-4245-9d75-9a0e4a28d825",
                            "value": "@results.avaliacao.category",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "b7205ca8-332b-491b-828d-977f926da067",
                            "uuid": "b553f5fa-0222-4e6f-b145-7c29c1533ecb",
                        }
                    ],
                    "uuid": "0d552af3-2d5e-4d82-a371-ea1630682cd6",
                },
                {
                    "actions": [
                        {
                            "field": {
                                "key": "nota_pesquisa_atendimento_humano",
                                "name": "Nota Pesquisa Atendimento Humano",
                            },
                            "type": "set_contact_field",
                            "uuid": "80a9b3ab-955c-4730-b2b1-1d6841855d1a",
                            "value": "@results.avaliacao.category",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "b573a778-ceba-419b-b90c-648c67d01cdd",
                            "uuid": "d8458de9-3b0e-4456-a70a-225b5dcb79f5",
                        }
                    ],
                    "uuid": "3c5eb7ee-2ca9-4ef1-a0ce-3d3aeaa4caee",
                },
                {
                    "actions": [
                        {
                            "attachments": [],
                            "quick_replies": [],
                            "text": "Deixe um coment\u00e1rio sobre sua experi\u00eancia com nosso atendimento \u270d\ufe0f",
                            "type": "send_msg",
                            "uuid": "b6eeb06b-5e7f-4df4-b857-2f59f2d39a37",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "8ed3fdc1-52b6-4c94-ac8c-90a81f5de661",
                            "uuid": "2af349c0-9019-4d52-9de0-7bdceddeed21",
                        }
                    ],
                    "uuid": "b7205ca8-332b-491b-828d-977f926da067",
                },
                {
                    "actions": [
                        {
                            "attachments": [],
                            "quick_replies": [],
                            "text": "Deixe um coment\u00e1rio para sempre melhorarmos nosso atendimento \u270d\ufe0f",
                            "type": "send_msg",
                            "uuid": "898136db-4601-4f9f-a133-c323581e9dc2",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "947040c4-66ec-4cb8-9193-72277bf5a817",
                            "uuid": "2f823c77-a3e9-48c6-8924-eb42d5a32814",
                        }
                    ],
                    "uuid": "b573a778-ceba-419b-b90c-648c67d01cdd",
                },
                {
                    "actions": [
                        {
                            "category": "@results.avaliacao.category",
                            "name": "avaliacao",
                            "type": "set_run_result",
                            "uuid": "b2eea9f5-0cdb-44e7-b99c-4604ad57c9bf",
                            "value": "@results.avaliacao.category",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "35c6a45b-cacb-4949-8e00-e0227cd49c77",
                            "uuid": "9aa159f8-f183-4f71-80e1-72ba60f97bed",
                        }
                    ],
                    "uuid": "8ed3fdc1-52b6-4c94-ac8c-90a81f5de661",
                },
                {
                    "actions": [
                        {
                            "category": "@results.avaliacao.category",
                            "name": "avaliacao",
                            "type": "set_run_result",
                            "uuid": "66504dae-ecd9-488b-838f-261398a508e9",
                            "value": "@results.avaliacao.category",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "b6e40dc7-c7a3-4c72-b417-e1c8bf8867da",
                            "uuid": "3cf4f828-f1d8-4c25-9c3f-56485a872591",
                        }
                    ],
                    "uuid": "947040c4-66ec-4cb8-9193-72277bf5a817",
                },
                {
                    "actions": [],
                    "exits": [
                        {
                            "destination_uuid": "a69bba98-4c15-44f3-bd68-f5d8b62093f5",
                            "uuid": "02ac9c15-1cca-4235-a964-66e23f2c6d1c",
                        },
                        {
                            "destination_uuid": "0fc2dae0-49c7-4e09-9b6a-e4be0887088f",
                            "uuid": "ec6f4128-1169-44ce-85db-9f6f0f6e1253",
                        },
                    ],
                    "router": {
                        "cases": [],
                        "categories": [
                            {
                                "exit_uuid": "02ac9c15-1cca-4235-a964-66e23f2c6d1c",
                                "name": "All Responses",
                                "uuid": "9f65aa01-fd8d-4e3a-bcce-cfb684f16c45",
                            },
                            {
                                "exit_uuid": "ec6f4128-1169-44ce-85db-9f6f0f6e1253",
                                "name": "No Response",
                                "uuid": "2434e251-498a-42f4-8c78-dc723979fe73",
                            },
                        ],
                        "default_category_uuid": "9f65aa01-fd8d-4e3a-bcce-cfb684f16c45",
                        "operand": "@input.text",
                        "result_name": "comentario",
                        "type": "switch",
                        "wait": {
                            "timeout": {
                                "category_uuid": "2434e251-498a-42f4-8c78-dc723979fe73",
                                "seconds": 900,
                            },
                            "type": "msg",
                        },
                    },
                    "uuid": "35c6a45b-cacb-4949-8e00-e0227cd49c77",
                },
                {
                    "actions": [],
                    "exits": [
                        {
                            "destination_uuid": "82fa6589-e918-455d-a6f9-cd0ccda9142f",
                            "uuid": "058ada11-13c7-4e5b-85f4-9de5a74aa655",
                        },
                        {
                            "destination_uuid": "11a0c6d8-3752-4478-b7e0-79a96c98c244",
                            "uuid": "5e9845ed-7918-48a7-8813-c6b95d99397c",
                        },
                    ],
                    "router": {
                        "cases": [],
                        "categories": [
                            {
                                "exit_uuid": "058ada11-13c7-4e5b-85f4-9de5a74aa655",
                                "name": "All Responses",
                                "uuid": "2c6fc714-b0b8-4000-94a7-1dde8b82dd03",
                            },
                            {
                                "exit_uuid": "5e9845ed-7918-48a7-8813-c6b95d99397c",
                                "name": "No Response",
                                "uuid": "bcc4e0c2-1de0-4bd0-9548-929e03947be5",
                            },
                        ],
                        "default_category_uuid": "2c6fc714-b0b8-4000-94a7-1dde8b82dd03",
                        "operand": "@input.text",
                        "result_name": "comentario",
                        "type": "switch",
                        "wait": {
                            "timeout": {
                                "category_uuid": "bcc4e0c2-1de0-4bd0-9548-929e03947be5",
                                "seconds": 900,
                            },
                            "type": "msg",
                        },
                    },
                    "uuid": "b6e40dc7-c7a3-4c72-b417-e1c8bf8867da",
                },
                {
                    "actions": [
                        {
                            "attachments": [],
                            "text": "Seu atendimento foi finalizado.\n\nAgradecemos a sua colabora\u00e7\u00e3o. At\u00e9 a pr\u00f3xima \ud83d\udc4b",
                            "type": "send_msg",
                            "quick_replies": [],
                            "uuid": "246fff75-bb2d-469e-8394-2900cdbe6d84",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "dd2320a5-4001-41ca-9460-fc80dc96e1ef",
                            "uuid": "744a912d-2c42-43c7-8d94-9378743efe54",
                        }
                    ],
                    "uuid": "a69bba98-4c15-44f3-bd68-f5d8b62093f5",
                },
                {
                    "actions": [
                        {
                            "category": "N\u00e3o respondente",
                            "name": "comentario",
                            "type": "set_run_result",
                            "uuid": "accf712c-a3ca-47c8-8853-e4cc834812cc",
                            "value": "N\u00e3o respondente",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "dd2320a5-4001-41ca-9460-fc80dc96e1ef",
                            "uuid": "26e39e91-0303-494b-b3b2-50edc63f2750",
                        }
                    ],
                    "uuid": "0fc2dae0-49c7-4e09-9b6a-e4be0887088f",
                },
                {
                    "actions": [
                        {
                            "attachments": [],
                            "quick_replies": [],
                            "text": "Seu atendimento foi finalizado. Iremos analisar seu coment\u00e1rio com responsabilidade. \n\nAgradecemos a sua colabora\u00e7\u00e3o para melhorar o atendimento. At\u00e9 a pr\u00f3xima \ud83d\udc4b",
                            "type": "send_msg",
                            "uuid": "4d2bd028-62d2-454b-a9d4-0b2e3e4c1cc4",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "dd2320a5-4001-41ca-9460-fc80dc96e1ef",
                            "uuid": "ae8f87d5-a477-4747-bc4f-24da2161b1c7",
                        }
                    ],
                    "uuid": "82fa6589-e918-455d-a6f9-cd0ccda9142f",
                },
                {
                    "actions": [
                        {
                            "category": "N\u00e3o respondente",
                            "name": "comentario",
                            "type": "set_run_result",
                            "uuid": "5c9aeefb-d0bc-46bb-a764-5a3b7f304650",
                            "value": "N\u00e3o respondente",
                        }
                    ],
                    "exits": [
                        {
                            "destination_uuid": "dd2320a5-4001-41ca-9460-fc80dc96e1ef",
                            "uuid": "f700c5d9-d429-4729-bcbc-d708efdfe7a0",
                        }
                    ],
                    "uuid": "11a0c6d8-3752-4478-b7e0-79a96c98c244",
                },
                {
                    "uuid": "dd2320a5-4001-41ca-9460-fc80dc96e1ef",
                    "actions": [
                        {
                            "uuid": "c0b05d49-7bad-48bb-89be-d6774a21f83d",
                            "headers": {
                                "Accept": "application/json",
                                "Authorization": "Token @trigger.params.token",
                                "Content-Type": "application/json",
                            },
                            "type": "call_webhook",
                            "url": "@trigger.params.webhook_url",
                            "body": '@(json(object(\n  "contact", object(\n    "uuid", contact.uuid, \n    "name", contact.name, \n    "urn", contact.urn\n  ),\n  "flow", object(\n    "uuid", run.flow.uuid, \n    "name", run.flow.name\n  ),\n  "room", trigger.params.room,\n  "rating", results.avaliacao.value,\n  "comment", results.comentario.value\n)))',
                            "method": "POST",
                            "result_name": "Result",
                        }
                    ],
                    "router": {
                        "type": "switch",
                        "operand": "@results.result.category",
                        "cases": [
                            {
                                "uuid": "e1f11f07-9d81-4087-90d5-a22713d264e3",
                                "type": "has_only_text",
                                "arguments": ["Success"],
                                "category_uuid": "1fde0035-1904-4c3e-8049-0b6660ebca9c",
                            }
                        ],
                        "categories": [
                            {
                                "uuid": "1fde0035-1904-4c3e-8049-0b6660ebca9c",
                                "name": "Success",
                                "exit_uuid": "1a08464c-612a-492d-8c1f-ec90acd1e882",
                            },
                            {
                                "uuid": "931baa3c-abd8-4651-bc65-e26015283aac",
                                "name": "Failure",
                                "exit_uuid": "5be578e2-0fb6-49b9-b2b7-aa9541a9e61f",
                            },
                        ],
                        "default_category_uuid": "931baa3c-abd8-4651-bc65-e26015283aac",
                    },
                    "exits": [
                        {
                            "uuid": "1a08464c-612a-492d-8c1f-ec90acd1e882",
                            "destination_uuid": None,
                        },
                        {
                            "uuid": "5be578e2-0fb6-49b9-b2b7-aa9541a9e61f",
                            "destination_uuid": None,
                        },
                    ],
                },
            ],
            "spec_version": "13.1.0",
            "type": "messaging",
            "uuid": "fb488faa-4dba-4faf-8256-be993f851f7c",
            "revision": 99,
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
