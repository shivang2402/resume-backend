import re


def escape_latex(text: str) -> str:
    """Escape special LaTeX characters."""
    if not text:
        return ""
    
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


def generate_experience_entry(exp: dict) -> str:
    """Generate LaTeX for a single experience entry."""
    title = exp.get('title', '')
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
        items += f"    \\resumeItem{{{escape_latex(bullet)}}}\n"
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
    
    header = f"\\resumeProjectHeading\n"
    header += f"    {{\\textbf{{{escape_latex(name)}}} $|$ \\textit{{{escape_latex(tech)}}}}} {{}}\n"
    
    items = "\\resumeItemListStart\n"
    for bullet in bullets:
        items += f"    \\resumeItem{{{escape_latex(bullet)}}}\n"
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
    
    for category, items in skills.items():
        if isinstance(items, list):
            items_str = ", ".join(items) + "."
        else:
            items_str = items
        content += f"    \\textbf{{{escape_latex(category)}:}} & {escape_latex(items_str)}\\\\\n"
    
    if append:
        content += f"    & {escape_latex(append)}\\\\\n"
    
    content += "\\end{tabular}\n"
    return content


def generate_heading_tex(heading: dict) -> str:
    """Generate heading.tex content."""
    name = heading.get('name', '')
    location = heading.get('location', '')
    phone = heading.get('phone', '')
    email = heading.get('email', '')
    linkedin = heading.get('linkedin', '')
    github = heading.get('github', '')
    
    content = "%----------HEADING----------%\n"
    content += "\\begin{center}\n"
    content += f"    \\textbf{{\\huge {escape_latex(name)}}} \\\\ \\vspace{{3pt}}\n"
    content += "    \n"
    content += "    \\quad\n"
    content += f"    {{\\seticon{{faMapMarker}} \\underline{{{escape_latex(location)}}}}}\n"
    content += "    \\quad\n"
    content += f"    \\href{{tel:{phone}}}{{\\seticon{{faPhone}} \\underline{{{escape_latex(phone)}}}}}\n"
    content += "    \\quad\n"
    content += f"    \\href{{mailto:{email}}}{{\\seticon{{faEnvelope}} \\underline{{{escape_latex(email)}}}}}\n"
    content += "    \\quad\n"
    content += f"    \\href{{https://www.linkedin.com/in/{linkedin}}}{{\\seticon{{faLinkedin}} \\underline{{{escape_latex(linkedin)}}}}}\n"
    content += "    \\quad\n"
    content += f"    \\href{{https://github.com/{github}}}{{\\seticon{{faGithub}} \\underline{{{escape_latex(github)}}}}}\n"
    content += "    \\quad\n"
    content += "\\end{center}\n"
    return content