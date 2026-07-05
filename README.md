# project-bmo

A terminal chatbot that classifies user input into intents (defined in `intents.json`) using a small Keras neural net, then replies with a matching canned response.

## Requirements

- Python 3.10 (see `.python-version`)
- Dependencies in `requirements.txt`

## Setup

Using conda:

```
conda create -n project-bmo python=3.10 -y
conda activate project-bmo
pip install -r requirements.txt
```

Or with venv:

```
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Then download the required NLTK data (one-time):

```
python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('wordnet'); nltk.download('omw-1.4')"
```

## Training

Edit `intents.json` to add/change tags, patterns, and responses, then run:

```
python training.py
```

This writes `model/words.pkl`, `model/classes.pkl`, and `model/chatbotmodel.h5`. Re-run this any time `intents.json` changes.

## Running

```
python bmo.py
```

Chat at the `>` prompt. Type `quit` or `exit` to stop.
