"""Optional questions only; provider failure must not discard the rules result."""
import json
import logging
import os
import httpx

log = logging.getLogger('worker')


def add_optional_questions(analysis, context):
    if os.getenv('AI_PAID_PROCESSING_APPROVED', 'false').lower() != 'true' or not os.getenv('OPENAI_API_KEY'):
        return
    try:
        response = httpx.post(
            'https://api.openai.com/v1/chat/completions',
            headers={'Authorization': 'Bearer ' + os.environ['OPENAI_API_KEY']},
            json={'model': os.getenv('OPENAI_MODEL', 'gpt-4.1-mini'), 'store': False,
                  'max_completion_tokens': 300, 'messages': [
                      {'role': 'system', 'content': 'Zwróć wyłącznie neutralne pytania po polsku. Nie twórz faktów, decyzji ani wiadomości do wysłania.'},
                      {'role': 'user', 'content': json.dumps(context, ensure_ascii=False)}]},
            timeout=60)
        response.raise_for_status()
        questions = response.json()['choices'][0]['message']['content']
        if not isinstance(questions, str) or not questions.strip() or len(questions) > 5000:
            raise ValueError('Invalid provider result')
    except Exception:
        analysis['model_status'] = 'unavailable'
        log.warning('Optional AI unavailable; retaining rules result; no customer action performed')
        return
    analysis['model_questions_unverified'] = questions
    analysis['engine'] = 'rules+openai_questions'
    analysis['model_status'] = 'available'
