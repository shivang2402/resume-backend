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
            context_parts = []
            
            for section_type, refs in resume_config.items():
                if isinstance(refs, list):
                    for ref in refs:
                        parts = ref.split(":")
                        if len(parts) >= 3:
                            key, flavor, version = parts[0], parts[1], parts[2]
                            section = db.query(Section).filter(
                                Section.user_id == user_id,
                                Section.type == section_type.rstrip('s'),
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
        
        template = db.query(OutreachTemplate).filter(
            OutreachTemplate.id == template_id,
            OutreachTemplate.user_id == user_id
        ).first()
        
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        
        resume_context = cls._fetch_resume_context(db, user_id, resume_config)
        
        prompt = cls._build_generation_prompt(
            template_content=template.content,
            style=template.style,
            length=template.length,
            company=company,
            contact_name=contact_name,
            resume_context=resume_context,
            additional_context=additional_context
        )
        
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
- Look for patterns like "Me:", "Them:", "SENT", "RECEIVED", timestamps, or indentation to determine direction
- Messages marked "SENT" are from the user (direction: "sent")
- Messages marked "RECEIVED" are from the contact (direction: "received")
- Clean up the message content (remove leading timestamps, direction labels, etc.)
- If no clear timestamp, set message_at to null

**RESPOND IN THIS EXACT JSON FORMAT (no markdown, no code blocks):**
{{"messages": [{{"direction": "sent", "content": "message text here", "message_at": "2026-01-15T14:30:00"}}]}}

If you cannot parse the conversation at all, respond with:
{{"error": "Could not parse conversation"}}"""
        
        try:
            model = cls._get_gemini_client(api_key)
            response = model.generate_content(prompt)
            
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
        
        # Get all messages in the thread, ordered by time
        messages = db.query(OutreachMessage).filter(
            OutreachMessage.thread_id == thread_id
        ).order_by(OutreachMessage.message_at.asc().nullsfirst(), OutreachMessage.created_at.asc()).all()
        
        if not messages:
            raise HTTPException(status_code=400, detail="Thread has no messages to reply to")
        
        # Find the last received message (this is what we're replying to)
        last_received = None
        for msg in reversed(messages):
            if msg.direction == "received":
                last_received = msg
                break
        
        # Find the last sent message (for context on where we left off)
        last_sent = None
        for msg in reversed(messages):
            if msg.direction == "sent":
                last_sent = msg
                break
        
        # Build conversation history (last 10 messages for context)
        recent_messages = messages[-10:] if len(messages) > 10 else messages
        history_lines = []
        for msg in recent_messages:
            if msg.direction == "sent":
                direction_label = "ME (you - the job seeker)"
            else:
                direction_label = f"THEM ({thread.contact_name or 'contact'} at {thread.company})"
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
        
        # Determine conversation state
        if last_received and last_sent:
            if messages[-1].direction == "received":
                conv_state = "They sent the last message. You need to reply to them."
            else:
                conv_state = "You sent the last message. You may be following up since they haven't replied."
        elif last_received and not last_sent:
            conv_state = "They reached out first. This is your first reply to them."
        elif last_sent and not last_received:
            conv_state = "You reached out first and are following up."
        else:
            conv_state = "Starting a new conversation."
        
        prompt = f"""You are helping write a reply in an ongoing job-related LinkedIn conversation.

**CONTACT:** {thread.contact_name or 'Unknown'} at {thread.company}

**CONVERSATION STATE:** {conv_state}

**RECENT CONVERSATION HISTORY (oldest to newest):**
{history}

"""
        
        if last_received:
            prompt += f"""**THE LAST MESSAGE FROM THEM (this is what you're replying to):**
{last_received.content[:500]}{'...' if len(last_received.content) > 500 else ''}

"""
        
        if last_sent:
            prompt += f"""**YOUR LAST MESSAGE (for context):**
{last_sent.content[:300]}{'...' if len(last_sent.content) > 300 else ''}

"""
        
        prompt += f"""**YOUR BACKGROUND:**
{resume_context}

**STYLE:** {style_instructions.get(style, 'professional but approachable')}
**MAX LENGTH:** {char_limit} characters

"""
        
        if instructions:
            prompt += f"""**SPECIFIC INSTRUCTIONS FROM USER:**
{instructions}

"""
        
        prompt += """**INSTRUCTIONS:**
1. Write a natural reply that responds to their last message
2. Reference your background ONLY if relevant to what they said
3. Be helpful and move toward your goal (getting a referral, interview, info)
4. If they shared a job posting, express genuine interest and ask a relevant question
5. If they asked a question, answer it directly
6. Keep it concise and end with a clear next step or question
7. Output ONLY the reply text, no explanations or preamble

**YOUR REPLY:**"""
        
        model = cls._get_gemini_client(api_key)
        response = model.generate_content(prompt)
        reply = response.text.strip()
        
        if length == "short" and len(reply) > 300:
            reply = reply[:297] + "..."
        
        return {
            "message": reply,
            "char_count": len(reply)
        }

    @classmethod
    def generate_message(
        cls,
        db: Session,
        user_id: UUID,
        company: str,
        style: str = "semi_formal",
        length: str = "short",
        template_id: Optional[UUID] = None,
        contact_name: Optional[str] = None,
        jd_text: Optional[str] = None,
        application_id: Optional[UUID] = None,
        api_key: Optional[str] = None
    ) -> dict:
        """Generate a cold outreach message."""
        from app.models.application import Application
        
        template_content = ""
        if template_id:
            template = db.query(OutreachTemplate).filter(
                OutreachTemplate.id == template_id,
                OutreachTemplate.user_id == user_id
            ).first()
            if template:
                template_content = f"Use this as inspiration:\n{template.content}"
                style = template.style
                length = template.length
        
        app_context = ""
        if application_id:
            app = db.query(Application).filter(
                Application.id == application_id,
                Application.user_id == user_id
            ).first()
            if app:
                app_context = f"Role: {app.role} at {app.company}"
                if app.job_url:
                    app_context += f"\nJob URL: {app.job_url}"
        
        resume_context = cls._fetch_resume_context(db, user_id)
        
        char_limit = 300 if length == "short" else 600
        
        style_guidance = {
            "professional": "Use formal, professional language. Be respectful and business-like.",
            "semi_formal": "Use a friendly but professional tone. Balance warmth with professionalism.",
            "casual": "Use a relaxed, conversational tone. Be friendly and approachable.",
            "friend": "Write as if messaging a friend. Be warm, casual, and genuine."
        }
        
        prompt = f"""Generate a cold outreach message for job networking.

**TARGET:**
- Company: {company}
- Contact: {contact_name or "a professional at the company"}

**STYLE:** {style}
{style_guidance.get(style, style_guidance["semi_formal"])}

**LENGTH:** Maximum {char_limit} characters (this is STRICT for short messages)

**SENDER'S BACKGROUND:**
{resume_context}

"""
        
        if template_content:
            prompt += f"""**TEMPLATE TO FOLLOW:**
{template_content}

"""
        
        if jd_text:
            prompt += f"""**JOB DESCRIPTION CONTEXT:**
{jd_text[:1000]}

"""
        
        if app_context:
            prompt += f"""**APPLICATION CONTEXT:**
{app_context}

"""
        
        prompt += """**INSTRUCTIONS:**
1. Write a concise, personalized cold outreach message
2. Reference specific relevant experience from the sender's background
3. Make it clear what you're asking for (referral, coffee chat, advice, etc.)
4. Do NOT use generic phrases like "I'm excited" or "I'm passionate"
5. Do NOT start with "I hope this message finds you well"
6. Be specific and genuine
7. Output ONLY the message text, no explanations

**GENERATE THE MESSAGE:**"""
        
        model = cls._get_gemini_client(api_key)
        response = model.generate_content(prompt)
        message = response.text.strip()
        
        if length == "short" and len(message) > 300:
            message = message[:297] + "..."
        
        return {
            "message": message
        }