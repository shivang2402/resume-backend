import re


def escape_latex(text) -> str:
    """Escape special LaTeX characters."""
    if not text:
        return ""
    
    # Handle lists by joining them
    if isinstance(text, list):
        text = ", ".join(str(item) for item in text)
    
    # Ensure it's a string
    text = str(text)
    
    # Characters that need escaping in LaTeX
    replacements = [
        ('\\', r'\textbackslash{}'),
        ('&', r'\&'),
        ('%', r'\%'),
        ('$', r'\$'),
        ('#', r'\#'),
        ('_', r'\_'),
        ('{', r'\{'),
        ('}', r'\}'),
        ('~', r'\textasciitilde{}'),
        ('^', r'\textasciicircum{}'),
    ]
    
    for old, new in replacements:
        text = text.replace(old, new)
    
    return text


def process_bullet(text: str) -> str:
    """
    Process a bullet point: convert markdown bold/italic to LaTeX,
    then escape special characters in the non-formatted parts.
    
    Supports:
        **bold text** -> \\textbf{bold text}
        *italic text* -> \\textit{italic text}
    """
    if not text:
        return ""
    
    if not isinstance(text, str):
        text = str(text)
    
    # Split text into segments: markdown-formatted and plain text.
    # We process bold first (**...**), then italic (*...*).
    # 
    # Strategy: find all **bold** and *italic* spans, escape the plain
    # text between them, and wrap the formatted spans in LaTeX commands.
    
    result = []
    i = 0
    
    while i < len(text):
        # Check for bold: **...**
        if text[i:i+2] == '**':
            end = text.find('**', i + 2)
            if end != -1:
                inner = escape_latex(text[i+2:end])
                result.append(f'\\textbf{{{inner}}}')
                i = end + 2
                continue
        
        # Check for italic: *...*
        if text[i] == '*':
            end = text.find('*', i + 1)
            if end != -1:
                inner = escape_latex(text[i+1:end])
                result.append(f'\\textit{{{inner}}}')
                i = end + 1
                continue
        
        # Plain text: collect until next * 
        next_star = text.find('*', i)
        if next_star == -1:
            result.append(escape_latex(text[i:]))
            break
        else:
            result.append(escape_latex(text[i:next_star]))
            i = next_star
    
    return ''.join(result)


def generate_experience_entry(exp: dict) -> str:
    """Generate LaTeX for a single experience entry."""
    title = exp.get('title') or exp.get('role', '')
    company = exp.get('company', '')
    location = exp.get('location', '')
    dates = exp.get('dates', '')
    bullets = exp.get('bullets', [])
    
    # Build the header line
    header = f"\\resumeSubheadingExp\n"
    header += f"    {{\\textbf{{{escape_latex(title)}}} $|$ \\textbf{{\\textit{{{escape_latex(company)}}}}} $|$ \\textit{{{escape_latex(location)}}}}}{{{escape_latex(dates)}}}\n"
    
    # Build bullets
    items = "\\resumeItemListStart\n"
    for bullet in bullets:
        items += f"    \\resumeItem{{{process_bullet(bullet)}}}\n"
    items += "\\resumeItemListEnd\n"
    
    return header + items


def generate_experience_tex(experiences: list[dict]) -> str:
    """Generate complete experience.tex content."""
    content = "%-----------EXPERIENCE-----------%\n"
    content += "\\section{Experience}\n"
    content += "\\resumeSubHeadingListStart\n\n"
    
    for exp in experiences:
        content += generate_experience_entry(exp)
        content += "\n"
    
    content += "\\resumeSubHeadingListEnd\n"
    return content


def generate_project_entry(proj: dict) -> str:
    """Generate LaTeX for a single project entry."""
    name = proj.get('name', '')
    tech = proj.get('tech', '')
    bullets = proj.get('bullets', [])
    
    # tech might be a list, escape_latex handles it
    header = f"\\resumeProjectHeading\n"
    header += f"    {{\\textbf{{{escape_latex(name)}}} $|$ \\textit{{{escape_latex(tech)}}}}} {{}}\n"
    
    items = "\\resumeItemListStart\n"
    for bullet in bullets:
        items += f"    \\resumeItem{{{process_bullet(bullet)}}}\n"
    items += "\\resumeItemListEnd\n"
    
    return header + items


def generate_projects_tex(projects: list[dict]) -> str:
    """Generate complete projects.tex content."""
    content = "%-----------PROJECTS-----------%\n"
    content += "\\section{Projects}\n"
    content += "\\resumeSubHeadingListStart\n\n"
    
    for proj in projects:
        content += generate_project_entry(proj)
        content += "\n"
    
    content += "\\resumeSubHeadingListEnd\n"
    return content


def generate_skills_tex(skills: dict, append: str = None) -> str:
    """Generate skills.tex content from skills dict."""
    content = "\\section{Skills}\n"
    content += "\\small\n"
    content += "\\begin{tabular}{ @{} p{0.15\\textwidth} p{0.80\\textwidth} @{} }\n"
    
    # Handle case where skills might have 'skills' key inside
    if 'skills' in skills and isinstance(skills['skills'], dict):
        skills = skills['skills']
    
    # Filter out non-skill keys like 'tags'
    skip_keys = {'tags', 'type', 'key', 'flavor', 'version'}
    
    for category, items in skills.items():
        if category in skip_keys:
            continue
        if isinstance(items, list):
            items_str = ", ".join(str(item) for item in items) + "."
        else:
            items_str = str(items)
        content += f"    \\textbf{{{escape_latex(category)}:}} & {escape_latex(items_str)}\\\\\n"
    
    if append:
        content += f"    & {escape_latex(append)}\\\\\n"
    
    content += "\\end{tabular}\n"
    return content


# Default heading values (your static info)
DEFAULT_HEADING = {
    "name": "Shivang Patel",
    "location": "Seattle, WA",
    "phone": "+18575449579",
    "phone_display": "(857)-544-9579",
    "email": "patelshivang.work@gmail.com",
    "linkedin": "shivangmpatel",
    "github": "shivang2402",
}


def generate_heading_tex(heading: dict = None, location: str = None, email: str = None) -> str:
    """
    Generate heading.tex content.
    
    Args:
        heading: Optional dict with heading fields (name, phone, linkedin, github, etc.)
        location: Optional location override from location section
        email: Optional email override from email section
    
    Location and email overrides take precedence over heading dict values.
    """
    # Start with defaults
    h = DEFAULT_HEADING.copy()
    
    # Override with heading dict if provided
    if heading:
        h.update({k: v for k, v in heading.items() if v})
    
    # Override with location/email sections if provided
    if location:
        h["location"] = location
    if email:
        h["email"] = email
    
    # Get display values
    name = h.get("name", "")
    loc = h.get("location", "")
    phone = h.get("phone", "")
    phone_display = h.get("phone_display", phone)
    email_addr = h.get("email", "")
    linkedin = h.get("linkedin", "")
    github = h.get("github", "")
    
    content = "%----------HEADING----------%\n"
    content += "\\begin{center}\n"
    content += f"    \\textbf{{\\huge {escape_latex(name)}}} \\\\ \\vspace{{3pt}}\n"
    content += "    \n"
    content += "    \\quad\n"
    content += f"    {{\\seticon{{faMapMarker}} \\underline{{{escape_latex(loc)}}}}}\n"
    content += "    \\quad\n"
    content += f"    \\href{{tel:{phone}}}{{\\seticon{{faPhone}} \\underline{{{escape_latex(phone_display)}}}}}\n"
    content += "    \\quad\n"
    content += f"    \\href{{mailto:{email_addr}}}{{\\seticon{{faEnvelope}} \\underline{{{escape_latex(email_addr)}}}}}\n"
    content += "    \\quad\n"
    content += f"    \\href{{https://www.linkedin.com/in/{linkedin}}}{{\\seticon{{faLinkedin}} \\underline{{{escape_latex(linkedin)}}}}}\n"
    content += "    \\quad\n"
    content += f"    \\href{{https://github.com/{github}}}{{\\seticon{{faGithub}} \\underline{{{escape_latex(github)}}}}}\n"
    content += "    \\quad\n"
    content += "\\end{center}\n"
    return content