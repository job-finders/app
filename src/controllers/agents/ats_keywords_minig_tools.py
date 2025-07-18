




class IndustryTaxonomyTool(KeywordTool):
    source_type = KeywordSourceType.INDUSTRY_TAXONOMY

    def fetch(self, job: ATSOptimisationInput) -> List[tuple[str, int]]:
        # TODO: query your taxonomy service here
        return [("python", 42), ("django", 18)]


class PeerJobsTool(KeywordTool):
    source_type = KeywordSourceType.PEER_JOBS

    def fetch(self, job: ATSOptimisationInput) -> List[tuple[str, int]]:
        # TODO: run a similarity search against historical jobs
        return [("rest api", 30), ("postgresql", 25)]


class ParsedCVsTool(KeywordTool):
    source_type = KeywordSourceType.PARSED_CVS

    def fetch(self, job: ATSOptimisationInput) -> List[tuple[str, int]]:
        # TODO: aggregate keywords from CVs of similar roles
        return [("fastapi", 20), ("asyncio", 12)]

        