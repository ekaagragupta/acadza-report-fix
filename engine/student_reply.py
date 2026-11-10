from typing import Optional

class StudentReplyGenerator:
    """
    Generates empathetic, respectful, jargon-free replies for 17-year-old JEE/NEET aspirants.
    Rules:
    - 1-3 sentences maximum.
    - Never condescending.
    - If student is wrong, clearly point out the exact step or formula confusion.
    - If fixed, thank them sincerely.
    - If platform issue or under review, give reassurance.
    - Never leak internal terms (e.g. 'scope guard', 'classifier', 'taxonomy', 'regex').
    """

    @classmethod
    def generate_reply(
        cls,
        verdict: str,
        repair: Optional[str],
        confusion_reason: Optional[str] = None,
        is_adversarial: bool = False,
        fixed_summary: Optional[str] = None
    ) -> str:
        if is_adversarial:
            return "Thank you for contacting Acadza. Your report has been routed to our academic review team."

        if verdict == "no_error":
            if confusion_reason:
                return f"We reviewed this question carefully. {confusion_reason} The keyed answer is verified and correct. Keep pushing forward with your practice!"
            return "We reviewed this question thoroughly. The given answer and steps are scientifically accurate according to the standard syllabus. Best of luck with your preparation!"

        if verdict == "defect":
            if fixed_summary:
                return f"You're completely right! {fixed_summary} Thank you so much for bringing this to our attention—it helps all students preparing with Acadza."
            return "Thank you for pointing this out. Our academic team has verified the issue and is updating the question immediately. Good luck with your studies!"

        if verdict == "display_issue":
            return "Thanks for flagging this display issue! Our mobile and web engineering team is optimizing the layout so it renders cleanly across all devices."

        if verdict == "app_issue":
            return "We understand your frustration! Our technical team is investigating this response-recording glitch to ensure your marks reflect accurately."

        if verdict == "language_mode":
            return "Thank you for the request! We are actively translating questions into Hindi and regional languages. We appreciate your patience as we roll this out."

        if verdict == "not_actionable":
            return "We received your report, but couldn't identify the specific issue from the comment. If you notice any problem with this question, please feel free to report it with more details."

        return "Thank you for your feedback. Our academic team has noted this and is reviewing it."
