"""Command detection for direct execution vs AI routing"""
from dataclasses import dataclass
from typing import Optional, Set
from enum import Enum
import re


class InputType(Enum):
    """Classification of user input types"""
    DIRECT_COMMAND = "direct_command"
    AI_QUERY = "ai_query"
    INTERNAL_COMMAND = "internal_command"


@dataclass
class DetectionResult:
    """Result of command detection analysis"""
    input_type: InputType
    command: Optional[str] = None
    args: Optional[str] = None
    original_input: str = ""


class CommandDetector:
    """Detects whether user input is a direct shell command or AI query."""
    
    # Commands that can be executed directly
    DIRECT_COMMANDS: Set[str] = {
        # Unix commands
        'ls', 'pwd', 'cd', 'cat', 'clear', 'echo', 'whoami', 'date',
        'mkdir', 'rmdir', 'touch', 'rm', 'cp', 'mv', 'head', 'tail',
        'wc', 'grep', 'find', 'which', 'env', 'export', 'tree',
        # Windows commands
        'dir', 'cls', 'type', 'copy', 'move', 'del', 'md', 'rd',
        'ren', 'set', 'hostname', 'ipconfig', 'systeminfo',
    }
    
    # Strong natural language indicators
    QUESTION_WORDS: Set[str] = {
        'what', 'which', 'where', 'when', 'why', 'who', 'how',
        'whose', 'whom', 'whats', 'wheres', 'whens', 'whys', 'hows'
    }
    
    MODAL_VERBS: Set[str] = {
        'can', 'could', 'would', 'should', 'will', 'shall', 'may', 'might', 'must'
    }
    
    PRONOUNS: Set[str] = {
        'i', 'you', 'we', 'they', 'he', 'she', 'it', 'me', 'us', 'them',
        'my', 'your', 'our', 'their', 'his', 'her', 'its'
    }
    
    ARTICLES: Set[str] = {'a', 'an', 'the'}
    
    CONJUNCTIONS: Set[str] = {
        'but', 'however', 'although', 'though', 'because', 'since',
        'unless', 'while', 'whereas', 'if', 'whether'
    }
    
    # Verb forms that indicate natural language
    PAST_TENSE_SUFFIXES: tuple = ('ed', 'en', 'ied')
    PROGRESSIVE_SUFFIXES: tuple = ('ing',)
    
    # Shell command indicators
    SHELL_OPERATORS: Set[str] = {'|', '>', '<', '>>', '<<', '&&', '||', ';', '&'}
    FLAG_PATTERN = re.compile(r'^-[a-zA-Z]|^--[a-zA-Z]')
    PATH_PATTERN = re.compile(r'[/\\][\w\-./\\]+')
    FILE_EXTENSION_PATTERN = re.compile(r'\.\w{2,4}(?:\s|$)')
    
    # Conversational phrases
    CONVERSATIONAL_STARTERS: Set[str] = {
        'please', 'thanks', 'thank you', 'sorry', 'excuse me',
        'hello', 'hi', 'hey', 'okay', 'ok'
    }
    
    def detect(self, user_input: str) -> DetectionResult:
        """Analyze user input and determine how to process it.
        
        Uses multiple heuristics to distinguish between shell commands and natural language:
        - Sentence structure analysis
        - Word patterns (questions, pronouns, articles)
        - Shell-specific indicators (flags, pipes, paths)
        - Length and complexity
        - Verb tense analysis
        
        Args:
            user_input: The raw user input string
            
        Returns:
            DetectionResult with classification and parsed components
        """
        # Handle empty or whitespace-only input
        if not user_input or not user_input.strip():
            return DetectionResult(
                input_type=InputType.AI_QUERY,
                original_input=user_input
            )
        
        stripped_input = user_input.strip()
        
        # Quick check: if it has strong shell indicators, likely a command
        if self._has_shell_indicators(stripped_input):
            parts = stripped_input.split(maxsplit=1)
            first_word = parts[0].lower()
            
            # But still check if first word is a known command
            if first_word in self.DIRECT_COMMANDS:
                return DetectionResult(
                    input_type=InputType.DIRECT_COMMAND,
                    command=first_word,
                    args=parts[1] if len(parts) > 1 else None,
                    original_input=user_input
                )
        
        # Split input into command and arguments
        parts = stripped_input.split(maxsplit=1)
        first_word = parts[0].lower()
        args = parts[1] if len(parts) > 1 else None
        
        # Check if first word is a known direct command
        if first_word in self.DIRECT_COMMANDS:
            # Apply comprehensive heuristics to detect natural language
            if self._is_natural_language(stripped_input, first_word, args):
                return DetectionResult(
                    input_type=InputType.AI_QUERY,
                    original_input=user_input
                )
            
            return DetectionResult(
                input_type=InputType.DIRECT_COMMAND,
                command=first_word,
                args=args,
                original_input=user_input
            )
        
        # Default to AI query for anything else
        return DetectionResult(
            input_type=InputType.AI_QUERY,
            original_input=user_input
        )
    
    def _is_natural_language(self, full_input: str, command: str, args: Optional[str]) -> bool:
        """Comprehensive heuristics to detect if input is natural language.
        
        Args:
            full_input: The complete user input
            command: The first word (potential command)
            args: The rest of the input after the first word
            
        Returns:
            True if input appears to be natural language, False if it looks like a shell command
        """
        if not args:
            # Single word commands are likely shell commands
            return False
        
        full_input_lower = full_input.lower()
        args_lower = args.lower()
        words = full_input_lower.split()
        
        # Score-based approach: accumulate evidence for natural language
        nl_score = 0
        
        # 1. Strong conversational indicators (high weight)
        strong_indicators = [
            'are you', 'do you', 'can you', 'will you', 'would you', 'could you',
            'should i', 'how do', 'what is', 'what are', 'why is', 'when is',
            'tell me', 'show me', 'explain', 'describe', 'help me',
            'i want', 'i need', 'i have', 'i am', 'i\'m'
        ]
        
        for indicator in strong_indicators:
            if indicator in full_input_lower:
                nl_score += 10
                break
        
        # 2. Question structure analysis
        if self._is_question_structure(full_input_lower, words):
            nl_score += 8
        
        # 3. Pronouns (strong indicator)
        if any(word in self.PRONOUNS for word in words):
            nl_score += 5
        
        # 4. Articles at the beginning or in args
        if words[0] in self.ARTICLES or any(word in self.ARTICLES for word in args_lower.split()):
            nl_score += 4
        
        # 5. Modal verbs (auxiliary verbs)
        if any(word in self.MODAL_VERBS for word in words):
            nl_score += 4
        
        # 6. Conjunctions (indicates complex sentence)
        if any(word in self.CONJUNCTIONS for word in words):
            nl_score += 3
        
        # 7. Conversational starters
        if any(full_input_lower.startswith(starter) for starter in self.CONVERSATIONAL_STARTERS):
            nl_score += 3
        
        # 8. Multiple sentences (periods, multiple clauses)
        if full_input.count('.') > 1 or full_input.count(',') > 1:
            nl_score += 3
        
        # 9. Length-based heuristic (natural language tends to be longer)
        word_count = len(words)
        if word_count > 10:
            nl_score += 3
        elif word_count > 6:
            nl_score += 2
        
        # 10. Verb tense analysis (past/progressive tense suggests natural language)
        if self._has_natural_language_verbs(words):
            nl_score += 4
        
        # 11. Question mark with question context
        if full_input.rstrip().endswith('?'):
            if any(word in self.QUESTION_WORDS for word in words):
                nl_score += 5
            else:
                nl_score += 2
        
        # 12. Special handling for specific commands
        nl_score += self._command_specific_checks(command, args_lower, words)
        
        # Negative indicators (shell command patterns)
        shell_score = 0
        
        # Flags and options
        if self.FLAG_PATTERN.search(args):
            shell_score += 5
        
        # Paths
        if self.PATH_PATTERN.search(args):
            shell_score += 3
        
        # File extensions
        if self.FILE_EXTENSION_PATTERN.search(args):
            shell_score += 2
        
        # Shell operators
        if any(op in full_input for op in self.SHELL_OPERATORS):
            shell_score += 5
        
        # Short and concise (typical shell command)
        if word_count <= 3 and not any(word in self.QUESTION_WORDS for word in words):
            shell_score += 4
        
        # Single argument without natural language indicators
        if word_count == 2 and nl_score < 5:
            shell_score += 3
        
        # Decision: if natural language score significantly outweighs shell score
        # Use a higher threshold to be more conservative
        return nl_score > shell_score + 7
    
    def _is_question_structure(self, text: str, words: list) -> bool:
        """Detect question structure patterns.
        
        Args:
            text: Lowercase input text
            words: List of words in the input
            
        Returns:
            True if input has question structure
        """
        if len(words) < 2:
            return False
        
        # Question word at start - but be careful with "which" and "find"
        # These can be shell commands, so require additional context
        if words[0] in self.QUESTION_WORDS:
            # For "which" and "find", require additional natural language context
            if words[0] in {'which', 'find'}:
                # Need pronouns, auxiliary verbs, or more question words
                if len(words) > 2:
                    remaining_words = words[1:]
                    if (any(w in self.PRONOUNS for w in remaining_words) or
                        any(w in self.MODAL_VERBS for w in remaining_words) or
                        any(w in self.QUESTION_WORDS for w in remaining_words) or
                        any(w in {'is', 'are', 'was', 'were', 'do', 'does', 'did'} for w in remaining_words)):
                        return True
                return False
            # Other question words are strong indicators
            return True
        
        # Auxiliary verb inversion: "do you", "can I", "is there", "are you"
        auxiliary_verbs = {'do', 'does', 'did', 'can', 'could', 'would', 'should', 
                          'will', 'is', 'are', 'was', 'were', 'have', 'has', 'had'}
        
        if words[0] in auxiliary_verbs and len(words) > 1:
            if words[1] in self.PRONOUNS or words[1] == 'there':
                return True
        
        # Question word in middle with auxiliary verb
        for i, word in enumerate(words[1:], 1):
            if word in self.QUESTION_WORDS and i > 0:
                return True
        
        return False
    
    def _has_natural_language_verbs(self, words: list) -> bool:
        """Check for verb forms that indicate natural language.
        
        Args:
            words: List of words in the input
            
        Returns:
            True if natural language verb forms are detected
        """
        for word in words:
            # Past tense (ended, created, removed)
            if len(word) > 4 and any(word.endswith(suffix) for suffix in self.PAST_TENSE_SUFFIXES):
                # Exclude common shell commands that end in 'ed'
                if word not in {'cd', 'sed', 'ed'}:
                    return True
            
            # Progressive form (running, working, listing)
            if len(word) > 5 and any(word.endswith(suffix) for suffix in self.PROGRESSIVE_SUFFIXES):
                # Check for "is/are/am + verb+ing" pattern
                word_idx = words.index(word)
                if word_idx > 0 and words[word_idx - 1] in {'is', 'are', 'am', 'was', 'were', 'been'}:
                    return True
        
        return False
    
    def _command_specific_checks(self, command: str, args_lower: str, words: list) -> int:
        """Special handling for specific commands that are often used in natural language.
        
        Args:
            command: The command word
            args_lower: Lowercase arguments
            words: All words in input
            
        Returns:
            Score adjustment for natural language likelihood
        """
        score = 0
        
        # "which" command - often used in questions, but be conservative
        if command == 'which':
            # Only treat as natural language if there's clear question context
            question_context = ['model', 'version', 'one', 'option', 'way', 'better', 'best', 'should', 'would']
            has_question_context = any(word in args_lower for word in question_context)
            
            # Check for question words or pronouns in the args
            args_words = args_lower.split()
            has_question_words = any(word in self.QUESTION_WORDS for word in args_words)
            has_pronouns = any(word in self.PRONOUNS for word in args_words)
            
            if has_question_context and (has_question_words or has_pronouns or len(args_words) > 3):
                score += 5
            elif has_question_words or (has_pronouns and len(args_words) > 2):
                score += 4
        
        # "find" command - can be natural language
        if command == 'find':
            if args_lower.startswith(('out', 'me', 'the way', 'how', 'a way')):
                score += 5
            # "find out", "find me", etc.
            if any(phrase in args_lower for phrase in ['find out', 'find me', 'find how']):
                score += 5
        
        # "cat" command - can be used in questions about cats (the animal)
        if command == 'cat' and any(word in words for word in ['my', 'a', 'the', 'your']):
            if not self.PATH_PATTERN.search(args_lower) and not self.FILE_EXTENSION_PATTERN.search(args_lower):
                score += 3
        
        # "date" command - can be about calendar dates
        if command == 'date':
            date_context = ['today', 'tomorrow', 'yesterday', 'when', 'what', 'is', 'the']
            if any(word in args_lower for word in date_context):
                score += 4
        
        # "echo" command - but "echo" can be in natural language
        if command == 'echo' and len(words) > 3:
            if any(word in self.PRONOUNS for word in words):
                score += 3
        
        return score
    
    def _has_shell_indicators(self, text: str) -> bool:
        """Quick check for strong shell command indicators.
        
        Args:
            text: The input text
            
        Returns:
            True if text has strong shell indicators
        """
        # Check for pipes, redirects, and other shell operators
        if any(op in text for op in self.SHELL_OPERATORS):
            return True
        
        # Check for flags at the start of arguments
        parts = text.split()
        if len(parts) > 1:
            for part in parts[1:]:
                if self.FLAG_PATTERN.match(part):
                    return True
        
        return False
