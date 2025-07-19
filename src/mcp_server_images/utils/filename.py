"""Filename templating utilities."""

import re
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


def extract_subject(prompt: str, max_length: int = 50) -> str:
    """Extract a clean subject from the prompt for filename use."""
    # Remove common prefixes and suffixes
    clean_prompt = prompt.lower()
    
    # Remove common prompt prefixes
    prefixes_to_remove = [
        "a ", "an ", "the ", "create ", "generate ", "make ", "draw ", "paint ",
        "digital painting of ", "artwork of ", "image of ", "picture of ",
        "realistic ", "detailed ", "highly detailed ", "professional ",
        "masterpiece ", "award-winning ", "stunning ", "beautiful "
    ]
    
    for prefix in prefixes_to_remove:
        if clean_prompt.startswith(prefix):
            clean_prompt = clean_prompt[len(prefix):]
            break
    
    # Remove common suffixes
    suffixes_to_remove = [
        " style", " art", " artwork", " painting", " image", " picture",
        " digital art", " concept art", " illustration", " render",
        " highly detailed", " professional", " masterpiece", " 4k", " 8k"
    ]
    
    for suffix in suffixes_to_remove:
        if clean_prompt.endswith(suffix):
            clean_prompt = clean_prompt[:-len(suffix)]
            break
    
    # Extract key subject words (first few meaningful words)
    words = re.findall(r'\b[a-zA-Z]+\b', clean_prompt)
    
    # Filter out common words
    common_words = {
        'with', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'from',
        'up', 'about', 'into', 'through', 'during', 'before', 'after', 'above',
        'below', 'between', 'among', 'very', 'really', 'quite', 'rather', 'too'
    }
    
    meaningful_words = [word for word in words if word.lower() not in common_words]
    
    # Take first 3-4 meaningful words
    subject_words = meaningful_words[:4] if meaningful_words else words[:4]
    subject = '_'.join(subject_words)
    
    # Truncate if too long
    if len(subject) > max_length:
        subject = subject[:max_length]
    
    # Ensure it's not empty
    if not subject:
        subject = "image"
    
    return subject


def generate_prompt_hash(prompt: str, length: int = 8) -> str:
    """Generate a short hash from the prompt."""
    return hashlib.md5(prompt.encode()).hexdigest()[:length]


def apply_filename_template(
    template: str,
    prompt: str,
    provider: str,
    model: str,
    counter: Optional[int] = None
) -> str:
    """Apply filename template with variable substitution."""
    
    now = datetime.now()
    
    # Template variables
    variables = {
        'Timestamp': now.strftime('%m%d%y.%H%M%S'),
        'Date': now.strftime('%m%d%y'),
        'Time': now.strftime('%H%M%S'),
        'Provider': provider.lower(),
        'Model': model.replace('.', '').replace('-', ''),
        'Subject': extract_subject(prompt),
        'Hash': generate_prompt_hash(prompt),
    }
    
    # Add counter if provided
    if counter is not None:
        variables['Counter'] = f"{counter:03d}"
    
    # Replace template variables
    filename = template
    for key, value in variables.items():
        filename = filename.replace(f'{{{{.{key}}}}}', str(value))
    
    # Clean up filename - remove any remaining template markers
    filename = re.sub(r'\{\{[^}]*\}\}', '', filename)
    
    # Ensure valid filename
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = re.sub(r'_+', '_', filename)  # Collapse multiple underscores
    filename = filename.strip('_')
    
    return filename


def generate_filename(
    template: str,
    prompt: str,
    provider: str,
    model: str,
    output_dir: Path,
    extension: str = "png",
    counter: Optional[int] = None
) -> Path:
    """Generate a complete file path with the given template."""
    
    # Apply template
    base_filename = apply_filename_template(template, prompt, provider, model, counter)
    
    # Add extension if not present
    if not base_filename.endswith(f'.{extension}'):
        base_filename = f"{base_filename}.{extension}"
    
    # Create full path
    output_path = Path(output_dir) / base_filename
    
    # Handle file conflicts by adding a number
    if output_path.exists():
        stem = output_path.stem
        suffix = output_path.suffix
        parent = output_path.parent
        
        conflict_counter = 1
        while output_path.exists():
            new_name = f"{stem}_{conflict_counter:03d}{suffix}"
            output_path = parent / new_name
            conflict_counter += 1
    
    return output_path


# Example usage and testing
if __name__ == "__main__":
    # Test the filename generation
    test_prompt = "A serene mountain landscape at sunset with a lake reflection"
    test_template = "{{.Timestamp}}-{{.Provider}}-{{.Subject}}"
    
    result = apply_filename_template(test_template, test_prompt, "stability", "sd3.5-large")
    print(f"Template: {test_template}")
    print(f"Prompt: {test_prompt}")
    print(f"Result: {result}")
    
    # Test subject extraction
    subjects = [
        "A serene mountain landscape at sunset",
        "Digital painting of a futuristic city",
        "Create a realistic portrait of an elderly wizard",
        "Highly detailed artwork of a dragon",
        "Beautiful anime girl with blue hair"
    ]
    
    for prompt in subjects:
        subject = extract_subject(prompt)
        print(f"{prompt} -> {subject}")