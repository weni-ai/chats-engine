from django.http import QueryDict


def get_filters_from_query_params(query_params: QueryDict) -> dict:
    return {
        key: (
            query_params.getlist(key)
            if len(query_params.getlist(key)) > 1
            else query_params.get(key)
        )
        for key in query_params
    }
