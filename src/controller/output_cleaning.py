import re


class OutputCleaning:
    @staticmethod
    def clean_output(raw_content: str) -> str:

        content = raw_content.strip()

        # Extract everything between the first '{' and the last '}'
        start_idx = content.find("{")
        end_idx = content.rfind("}")

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            content = content[start_idx : end_idx + 1]

        return content