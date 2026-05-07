STRINGS = {
    "pt_BR": {
        "menu": "Censo Anki Brasil",
        "welcome_title": "Bem-vindo ao Censo Anki Brasil",
        "welcome_text": "Este addon ajuda a comunidade a entender melhor como o Anki é usado: addons populares, versões, FSRS, revisões, áreas de estudo e outros dados agregados.\n\nNenhum conteúdo dos seus cards, decks, notas, campos, tags ou arquivos de mídia será enviado.\n\nAgora você pode preencher seu perfil. Todas as informações são opcionais e ajudam a deixar o censo mais útil.",
        "profile_reminder_title": "Atualize seu perfil do Censo Anki Brasil",
        "profile_reminder_text": "O próximo Censo Anki Brasil começa em breve. Para deixar os dados da comunidade mais fiéis, vale revisar rapidinho seu perfil. Todas as informações são opcionais. Obrigado por ajudar o Anki Brasil!",
        "collection_start_title": "O Censo Anki Brasil começou",
        "collection_start_text": "O Censo Anki Brasil deste semestre começou. Recomendamos revisar seu perfil para manter as informações atualizadas. O envio dos dados técnicos acontece automaticamente durante a janela de coleta.",
        "open_profile": "Atualizar perfil",
        "close": "Fechar",
        "ok": "OK",
    },
    "en": {
        "menu": "Censo Anki Brasil",
        "welcome_title": "Welcome to Censo Anki Brasil",
        "welcome_text": "This add-on helps the community understand how Anki is used: popular add-ons, versions, FSRS, reviews, study areas, and other aggregate data.\n\nNo content from your cards, decks, notes, fields, tags, or media files will be sent.\n\nYou can now fill in your profile. All fields are optional.",
        "profile_reminder_title": "Update your Censo Anki Brasil profile",
        "profile_reminder_text": "The next Censo Anki Brasil starts soon. Please quickly review your profile so community data stays accurate. All fields are optional. Thank you for helping Anki Brasil!",
        "collection_start_title": "Censo Anki Brasil has started",
        "collection_start_text": "This semester's Censo Anki Brasil has started. We recommend reviewing your profile to keep it updated. Technical data is sent automatically during the collection window.",
        "open_profile": "Update profile",
        "close": "Close",
        "ok": "OK",
    }
}

def t(key, lang="pt_BR"):
    return STRINGS.get(lang, STRINGS["pt_BR"]).get(key, STRINGS["pt_BR"].get(key, key))
