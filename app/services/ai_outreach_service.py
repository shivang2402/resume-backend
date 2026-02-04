import google.generativeai as genai
from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import Optional, List
from uuid import UUID

from app.models.section import Section
from app.models.outreach_template import OutreachTemplate
from app.models.outreach_thread import OutreachThread
from app.models.outreach_message import OutreachMessage
from app.config import settings


class AIOutreachService:
    """Service for AI-powered outreach message generation using Gemini."""

    @staticmethod
    def _get_gemini_client(api_key: Optional[str] = None):
        """Configure and return Gemini client."""
        key = api_key or getattr(settings, 'gemini_api_key', None)
        if not key:
            raise HTTPException(status_code=400, detail="Gemini API key not configured")
        genai.configure(api_key=key)
        return genai.GenerativeModel('gemini-2.5-flash')

    @staticmethod
    def _fetch_resume_context(db: Session, user_id: UUID, resume_config: Optional[dict] = None) -> str:
        """Fetch user's resume sections and format as context."""
        if resume_config:
            # Fetch specific sections from resume_config
            context_parts = []
            
            for section_type, refs in resume_config.items():
                if isinstance(refs, list):
                    for ref in refs:
                        parts = ref.split(":")
                        if len(parts) >= 3:
                            key, flavor, version = parts[0], parts[1], parts[2]
                            section = db.query(Section).filter(
                                Section.user_id == user_id,
                                Section.type == section_type.rstrip('s'),  # experiences -> experience
                                Section.key == key,
                                Section.flavor == flavor,
                                Section.version == version
                            ).first()
                            if section:
                                context_parts.append(f"**{section_type.title()}** - {key}:\n{section.content}")
                elif isinstance(refs, str):
                    parts = refs.split(":")
                    if len(parts) >= 2:
                        key, version = parts[0], parts[1]
                        section = db.query(Section).filter(
                            Section.user_id == user_id,
                            Section.type == section_type,
                            Section.key == key,
                            Section.version == version
                        ).first()
                        if section:
                            context_parts.append(f"**{section_type.title()}**:\n{section.content}")
            
            return "\n\n".join(context_parts) if context_parts else ""
        else:
            # Fetch all current sections
            sections = db.query(Section).filter(
                Section.user_id == user_id,
                Section.is_current == True
            ).all()
            
            context_parts = []
            for section in sections:
                content_str = str(section.content) if section.content else ""
                context_parts.append(f"**{section.type.title()}** ({section.key}/{section.flavor}):\n{content_str}")
            
            return "\n\n".join(context_parts) if context_parts else "No resume content available."

    @staticmethod
    def _fetch_thread_history(db: Session, thread_id: UUID) -> str:
        """Fetch conversation history for a thread."""
        messages = db.query(OutreachMessage).filter(
            OutreachMessage.thread_id == thread_id
        ).order_by(OutreachMessage.created_at.asc()).all()
        
        if not messages:
            return ""
        
        history_parts = []
        for msg in messages:
            direction_label = "You" if msg.direction == "sent" else "Them"
            history_parts.append(f"{direction_label}: {msg.content}")
        
        return "\n\n".join(history_parts)

    @staticmethod
    def _build_generation_prompt(
        template_content: str,
        style: str,
        length: str,
        company: str,
        contact_name: Optional[str],
        resume_context: str,
        additional_context: Optional[str] = None
    ) -> str:
        """Build the prompt for message generation."""
        
        length_guidance = {
            "short": "Keep the message concise, around 3-5 sentences. Get to the point quickly.",
            "long": "Write a more detailed message, around 6-10 sentences. Include more context and personalization."
        }
        
        style_guidance = {
            "professional": "Use formal, professional language. Be respectful and business-like.",
            "semi_formal": "Use a friendly but professional tone. Balance warmth with professionalism.",
            "casual": "Use a relaxed, conversational tone. Be friendly and approachable.",
            "friend": "Write as if messaging a friend. Be warm, casual, and genuine."
        }
        
        prompt = f"""You are helping craft a personalized cold outreach message.

**TEMPLATE TO FOLLOW:**
{template_content}

**STYLE:** {style}
{style_guidance.get(style, style_guidance["professional"])}

**LENGTH:** {length}
{length_guidance.get(length, length_guidance["short"])}

**TARGET:**
- Company: {company}
- Contact: {contact_name or "Unknown"}

**SENDER'S BACKGROUND (use relevant details to personalize):**
{resume_context}

"""
        
        if additional_context:
            prompt += f"""**ADDITIONAL CONTEXT:**
{additional_context}

"""
        
        prompt += """**INSTRUCTIONS:**
1. Follow the template structure but personalize it based on the sender's background
2. Make specific references to the sender's experience that would be relevant to {company}
3. Keep the tone consistent with the style setting
4. Do not use generic phrases like "I'm excited" or "I'm passionate" - be specific
5. Output ONLY the message text, no explanations or alternatives

**GENERATE THE MESSAGE:**"""
        
        return prompt

    @classmethod
    def generate_initial_message(
        cls,
        db: Session,
        user_id: UUID,
        template_id: UUID,
        company: str,
        contact_name: Optional[str] = None,
        resume_config: Optional[dict] = None,
        additional_context: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> str:
        """Generate an initial outreach message."""
        
        # Fetch template
        template = db.query(OutreachTemplate).filter(
            OutreachTemplate.id == template_id,
            OutreachTemplate.user_id == user_id
        ).first()
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        # Fetch resume context
        resume_context = cls._fetch_resume_context(db, user_id, resume_config)
        
        # Build prompt
        prompt = cls._build_generation_prompt(
            template_content=template.content,
            style=template.style,
            length=template.length,
            company=company,
            contact_name=contact_name,
            resume_context=resume_context,
            additional_context=additional_context
        )
        
        # Call Gemini
        model = cls._get_gemini_client(api_key)
        response = model.generate_content(prompt)
        
        return response.text.strip()

    @classmethod
    def generate_reply(
        cls,
        db: Session,
        user_id: UUID,
        thread_id: UUID,
        received_message: str,
        style: str = "professional",
        length: str = "short",
        additional_instructions: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> str:
        """Generate a reply based on conversation history."""
        
        # Verify thread ownership
        thread = db.query(OutreachThread).filter(
            OutreachThread.id == thread_id,
            OutreachThread.user_id == user_id
        ).first()
        
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        # Fetch conversation history
        history = cls._fetch_thread_history(db, thread_id)
        
        # Fetch resume context
        resume_context = cls._fetch_resume_context(db, user_id, thread.resume_config)
        
        prompt = f"""You are helping craft a reply to a cold outreach conversation.

**CONVERSATION HISTORY:**
{history}

**NEW MESSAGE FROM THEM:**
{received_message}

**YOUR BACKGROUND:**
{resume_context}

**STYLE:** {style}
**LENGTH:** {length}

"""
        
        if additional_instructions:
            prompt += f"""**ADDITIONAL INSTRUCTIONS:**
{additional_instructions}

"""
        
        prompt += """**INSTRUCTIONS:**
1. Write a thoughtful reply that continues the conversation naturally
2. Reference relevant parts of your background if appropriate
3. Be helpful and move the conversation toward your goal (getting a referral, interview, etc.)
4. Match the tone and energy of their message while staying within your style setting
5. Output ONLY the reply text, no explanations

**GENERATE THE REPLY:**"""
        
        model = cls._get_gemini_client(api_key)
        response = model.generate_content(prompt)
        
        return response.text.strip()

    @classmethod
    def refine_message(
        cls,
        original_message: str,
        refinement_instructions: str,
        api_key: Optional[str] = None
    ) -> str:
        """Refine an existing message based on user feedback."""
        
        prompt = f"""You are helping refine a cold outreach message.

**ORIGINAL MESSAGE:**
{original_message}

**REFINEMENT INSTRUCTIONS:**
{refinement_instructions}

**INSTRUCTIONS:**
1. Apply the refinement instructions to improve the message
2. Keep the core intent and structure unless specifically asked to change it
3. Output ONLY the refined message, no explanations

**REFINED MESSAGE:**"""
        
        model = cls._get_gemini_client(api_key)
        response = model.generate_content(prompt)
        
        return response.text.strip()

    @classmethod
    def refine_message(
        cls,
        original_message: str,
        refinement_instructions: str,
        style: Optional[str] = None,
        length: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> dict:
        """Refine an existing message based on user instructions."""
        
        char_limit = 300 if length == "short" else 600
        
        prompt = f"""You are helping refine a cold outreach message.

**ORIGINAL MESSAGE:**
{original_message}

**REFINEMENT INSTRUCTIONS:**
{refinement_instructions}

**CONSTRAINTS:**
- Style: {style or 'maintain current style'}
- Maximum length: {char_limit} characters (STRICT for short messages)

**INSTRUCTIONS:**
1. Apply the refinement instructions to improve the message
2. Keep the core intent and personalization unless specifically asked to change it
3. Maintain any specific details about the person's background
4. Output ONLY the refined message text, no explanations or preamble

**REFINED MESSAGE:**"""
        
        model = cls._get_gemini_client(api_key)
        response = model.generate_content(prompt)
        refined = response.text.strip()
        
        # Enforce char limit for short messages
        if length == "short" and len(refined) > 300:
            refined = refined[:297] + "..."
        
        return {
            "message": refined,
            "char_count": len(refined)
        }

    @classmethod
    def parse_conversation(
        cls,
        raw_text: str,
        api_key: Optional[str] = None
    ) -> dict:
        """Parse a raw conversation dump into structured messages."""
        import json
        
        prompt = f"""Parse this conversation into individual messages. For each message, determine:
1. Direction: "sent" (from the job seeker/user) or "received" (from the recruiter/contact)
2. Content: the message text (clean it up, remove timestamps from the text itself)
3. Timestamp: if visible in the conversation (format: ISO 8601, e.g., "2026-01-15T14:30:00")

**CONVERSATION TO PARSE:**
{raw_text}

**INSTRUCTIONS:**
- Look for patterns like "Me:", "Them:", timestamps, or indentation to determine direction
- If you see names, the first message sender is usually "sent" (the user reaching out)
- Clean up the message content (remove leading timestamps, names, etc.)
- If no clear timestamp, set message_at to null

**RESPOND IN THIS EXACT JSON FORMAT (no markdown, no code blocks):**
{{"messages": [{{"direction": "sent", "content": "message text here", "message_at": "2026-01-15T14:30:00"}}]}}

If you cannot parse the conversation at all, respond with:
{{"error": "Could not parse conversation"}}"""
        
        try:
            model = cls._get_gemini_client(api_key)
            response = model.generate_content(prompt)
            
            # Clean up response (remove markdown code blocks if present)
            response_text = response.text.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            result = json.loads(response_text)
            
            if "error" in result:
                return {
                    "success": False,
                    "messages": [],
                    "raw_fallback": raw_text
                }
            
            # Convert to proper format
            parsed_messages = []
            for m in result.get("messages", []):
                parsed_messages.append({
                    "direction": m.get("direction", "sent"),
                    "content": m.get("content", ""),
                    "message_at": m.get("message_at")
                })
            
            return {
                "success": True,
                "messages": parsed_messages,
                "raw_fallback": None
            }
            
        except Exception as e:
            # If parsing fails, return raw fallback
            return {
                "success": False,
                "messages": [],
                "raw_fallback": raw_text
            }

    @classmethod
    def generate_reply(
        cls,
        db,
        user_id,
        thread_id,
        instructions: Optional[str] = None,
        style: str = "semi_formal",
        length: str = "long",
        api_key: Optional[str] = None
    ) -> dict:
        """Generate a reply for an ongoing conversation thread."""
        from app.models.outreach_thread import OutreachThread
        from app.models.outreach_message import OutreachMessage
        from app.models.section import Section
        from fastapi import HTTPException
        
        # Get the thread
        thread = db.query(OutreachThread).filter(
            OutreachThread.id == thread_id,
            OutreachThread.user_id == user_id
        ).first()
        
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        # Get all messages in the thread
        messages = db.query(OutreachMessage).filter(
            OutreachMessage.thread_id == thread_id
        ).order_by(OutreachMessage.message_at.asc().nullsfirst(), OutreachMessage.created_at.asc()).all()
        
        if not messages:
            raise HTTPException(status_code=400, detail="Thread has no messages to reply to")
        
        # Build conversation history
        history_lines = []
        for msg in messages:
            direction_label = "ME" if msg.direction == "sent" else "THEM"
            history_lines.append(f"[{direction_label}]: {msg.content}")
        history = "\n\n".join(history_lines)
        
        # Get resume context
        sections = db.query(Section).filter(
            Section.user_id == user_id,
            Section.is_current == True
        ).all()
        
        resume_context = cls._fetch_resume_context(db, user_id) if sections else "No resume sections available."
        
        # Build the prompt
        style_instructions = {
            "professional": "formal and polished",
            "semi_formal": "professional but approachable",
            "casual": "friendly and conversational",
            "friend": "warm and familiar"
        }
        
        char_limit = 300 if length == "short" else 600
        
        prompt = f"""You are helping write a reply in an ongoing job-related conversation.

**CONVERSATION HISTORY:**
{history}

**YOUR BACKGROUND:**
{resume_context}

**COMPANY:** {thread.company}
**CONTACT:** {thread.contact_name or 'Unknown'}

**STYLE:** {style_instructions.get(style, 'professional but approachable')}
**MAX LENGTH:** {char_limit} characters

"""
        
        if instructions:
            prompt += f"""**SPECIFIC INSTRUCTIONS FROM USER:**
{instructions}

"""
        
        prompt += """**INSTRUCTIONS:**
1. Write a natural reply that continues the conversation
2. Reference your background if relevant to what they asked
3. Be helpful and move toward your goal (getting a referral, interview, info)
4. Match the conversation's energy while staying within your style
5. Keep it concise and actionable
6. Output ONLY the reply text, no explanations or preamble

**YOUR REPLY:**"""
        
        model = cls._get_gemini_client(api_key)
        response = model.generate_content(prompt)
        reply = response.text.strip()
        
        # Enforce char limit for short messages
        if length == "short" and len(reply) > 300:
            reply = reply[:297] + "..."
        
        return {
            "message": reply,
            "char_count": len(reply)
        }
