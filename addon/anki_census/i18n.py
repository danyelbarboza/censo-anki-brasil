STRINGS = {
    "pt_BR": {
        "menu": "Anki Census",
        "welcome_title": "Bem-vindo ao Anki Census",
        "welcome_text": "Este addon ajuda a comunidade global a entender melhor como o Anki é usado: addons populares, versões, FSRS, revisões, áreas de estudo e outros dados agregados.\n\nNenhum conteúdo dos seus cards, decks, notas, campos, tags ou arquivos de mídia será enviado.\n\nAgora você pode preencher seu perfil. Todas as informações são opcionais e ajudam a deixar o censo mais útil.",
        "profile_reminder_title": "Atualize seu perfil do Anki Census",
        "profile_reminder_text": "O próximo Anki Census começa em breve. Para deixar os dados da comunidade mais fiéis, vale revisar rapidinho seu perfil. Todas as informações são opcionais.",
        "collection_start_title": "O Anki Census começou",
        "collection_start_text": "O Anki Census deste semestre começou. Recomendamos revisar seu perfil para manter as informações atualizadas. O envio dos dados técnicos acontece automaticamente durante a janela de coleta.",
        "open_profile": "Atualizar perfil",
        "close": "Fechar",
        "ok": "OK",
    },
    "en": {
        "menu": "Anki Census",
        "welcome_title": "Welcome to Anki Census",
        "welcome_text": "This add-on helps the global community understand how Anki is used: popular add-ons, versions, FSRS, reviews, study areas, and other aggregate data.\n\nNo content from your cards, decks, notes, fields, tags, or media files will be sent.\n\nYou can now fill in your profile. All fields are optional.",
        "profile_reminder_title": "Update your Anki Census profile",
        "profile_reminder_text": "The next Anki Census starts soon. Please quickly review your profile so community data stays accurate. All fields are optional.",
        "collection_start_title": "Anki Census has started",
        "collection_start_text": "This semester's Anki Census has started. We recommend reviewing your profile to keep it updated. Technical data is sent automatically during the collection window.",
        "open_profile": "Update profile",
        "close": "Close",
        "ok": "OK",
    },
}


def t(key, lang="en"):
    """Return translated strings with fallback to English."""
    return STRINGS.get(lang, STRINGS["en"]).get(key, STRINGS["en"].get(key, key))
