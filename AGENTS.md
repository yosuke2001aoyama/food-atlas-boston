# AGENTS.md

## App

HomeTaste Boston is a consumer-facing Streamlit app for discovering Boston restaurants through lived-experience food knowledge.

## Core Philosophy

This project must avoid exclusionary language. Do not frame the app as "only natives can judge food." Frame it as lived-experience context for everyone.

Anyone can explore. People who grew up with, lived with, or deeply know a cuisine can add HomeTaste checks that help others understand what feels familiar, comforting, and culturally true.

HomeTaste is not here to police authenticity. Food has many versions, and diaspora food changes, adapts, and becomes local. The app adds context; it does not certify a single correct version of a cuisine.

## Preferred Terms

- HomeTaste Boston
- HomeTaste check
- HomeTaste Score
- lived experience
- cuisine
- food culture
- familiar
- tastes like home
- cultural context
- people who grew up with the cuisine
- people who know the cuisine from home, family, or long-term lived experience

## Forbidden Or Discouraged Terms

- native-approved
- real natives
- only people from X
- authenticity police
- certified authentic
- right people
- outsiders
- foreigners do not know
- ethnic food gatekeeping

Use "authentic" carefully. Prefer "feels familiar," "close to home," "culturally familiar," or "lived-experience context."

## Development Commands

```bash
pip install -r requirements.txt
streamlit run app.py
python3 -m py_compile app.py
```

## Done Criteria

- Visible app name is HomeTaste Boston.
- Hero includes "Find the places that taste like home — to someone."
- No visible Food Atlas Boston wording remains.
- No "right people" wording remains.
- Generic Rate/Reviews language is replaced with Add a Check, Voices, or HomeTaste checks.
- Countries metric is replaced or clarified as Cuisines.
- The check form captures relationship to cuisine.
- The check form requires a concrete explanation.
- Restaurant cards show HomeTaste Score and lived-experience check count.
- Issue reporting is labeled Report issue.
- Images have robust fallbacks and no broken visible UI.
- Empty states are friendly and culturally respectful.
