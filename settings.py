from torch import cuda
USE_CUDA = cuda.is_available()

ET_FEATURES = ['FFD', 'GD', 'TRT', 'nFixations', 'GPT']

LSTM_HIDDEN_UNITS = 128

NUM_EPOCHS = 30
BATCH_SIZE = 64
INITIAL_LR = 1e-4
DROPOUT_PROB = 0.5

WORD_EMBED_DIM = 300

# Directories
WORD_EMBED_MODEL_DIR = 'models/GoogleNews-vectors-negative300.bin'
TRAINED_ET_MODEL_DIR = 'models/ET-feature-predictor-{}'
