import vcr


def create_vcr(record_mode: str):
    """
    Create and return a configured VCR instance.

    This function does not activate VCR.
    It only defines configuration.
    """

    return vcr.VCR(
        record_mode=record_mode,
        cassette_library_dir=".vcr_cassettes",
        serializer="yaml",
        match_on=[
            "method",
            "scheme",
            "host",
            "port",
            "path",
            "query",
        ],
        decode_compressed_response=True,
    )
