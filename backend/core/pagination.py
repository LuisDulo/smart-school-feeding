def paginate_queryset(request, queryset, default_limit=50, max_limit=200):
    """
    Manual limit/offset pagination for plain APIView endpoints that build
    their own custom response dict (DRF's pagination classes assume a
    generic ListAPIView, which none of these views are).

    `limit`/`offset` are additive, optional query params — a caller that
    doesn't pass them gets exactly `default_limit` items from the start,
    matching the hard-coded `[:N]` slices this replaces, so nothing
    breaks for existing callers. A caller that wants the rest of the
    data can page through it via `offset` instead of it being silently
    dropped past the old fixed cutoff.

    IMPORTANT: any status/search filtering must already be applied to
    `queryset` before calling this — filtering after paginating (i.e.
    slicing first, then discarding non-matching rows) silently returns
    fewer results than the requested page size and misses matches that
    fall outside the slice entirely.

    Returns (page, meta) where `page` is the sliced queryset and `meta`
    is {'count', 'limit', 'offset', 'has_more'} — 'count' is the total
    number of rows matching every filter already applied to `queryset`.
    """
    try:
        limit = int(request.query_params.get('limit', default_limit))
    except (TypeError, ValueError):
        limit = default_limit
    limit = max(1, min(limit, max_limit))

    try:
        offset = int(request.query_params.get('offset', 0))
    except (TypeError, ValueError):
        offset = 0
    offset = max(0, offset)

    total = queryset.count()
    page = queryset[offset:offset + limit]

    return page, {
        'count': total,
        'limit': limit,
        'offset': offset,
        'has_more': offset + limit < total,
    }
