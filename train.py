import time
from argparse import ArgumentParser

import torch
import numpy as np

from datasets import CorpusAggregator
from model import EyeTrackingPredictor, init_word_embedding_from_word2vec
from settings import *


def iterate(dataloader, train=True):
    epoch_loss = 0.0
    # loss calculated on the real/original values (not scaled)
    epoch_loss_ = torch.Tensor([0, 0, 0, 0, 0])
    loss_ = 0  # placeholder to avoid errors
    for i, (sentences, et_targets, et_targets_orig) in enumerate(dataloader):
        sentences = sentences.type(torch.LongTensor)
        if USE_CUDA:
            sentences = sentences.cuda()
            et_targets = et_targets.cuda()

        et_preds = model(sentences)
        et_preds_inverse = torch.Tensor(
            [dataset.normalizer.inverse_transform(x)
             for x in et_preds.detach().cpu().numpy()])

        # starting from the padding index, make the prediction values 0
        for sent, et_pred, et_pred_inverse in zip(
                sentences, et_preds, et_preds_inverse):
            try:
                pad_start_idx = np.where(sent.cpu().numpy() == 0)[0][0]
            except IndexError:
                pad_start_idx = None
            et_pred[pad_start_idx:] = 0
            et_pred_inverse[pad_start_idx:] = 0

        loss = torch.sqrt(mse_loss(et_preds, et_targets))

        # calculate the loss PER FEATURE
        loss_ = torch.sqrt(torch.Tensor(
            [mse_loss(et_preds_inverse[:, :, i],
                      et_targets_orig[:, :, i]).item()
             for i in range(5)]))

        if train:
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        epoch_loss += loss.item()
        epoch_loss_ += loss_
    return epoch_loss / (i + 1), epoch_loss_ / (i + 1)


parser = ArgumentParser()
parser.add_argument('--zuco', default=False)
parser.add_argument('--provo', default=False)
parser.add_argument('--geco', default=False)
parser.add_argument('--normalize-aggregate', default=True)
parser.add_argument('--calculate-inverse-loss', default=True)
args = parser.parse_args()

if args.zuco is False and args.provo is False and args.geco is False:
    corpus_list = ['ZuCo', 'PROVO', 'GECO']  # add UCL later?
else:
    corpus_list = []
    if args.zuco is not False:
        corpus_list.append('ZuCo')
    if args.provo is not False:
        corpus_list.append('PROVO')
    if args.geco is not False:
        corpus_list.append('GECO')

dataset = CorpusAggregator(corpus_list, args.normalize_aggregate)
initial_word_embedding = init_word_embedding_from_word2vec(
    dataset.vocabulary.keys())
mse_loss = torch.nn.MSELoss()
# mse_loss = torch.nn.L1Loss()

print('--- PARAMETERS ---')
print('Learning Rate:', INITIAL_LR)
print('# Epochs:', NUM_EPOCHS)
print('LSTM Hidden Units:', LSTM_HIDDEN_UNITS)
print('Number of sentences:', len(dataset))
print('\n--- Starting training (10-CV) ---')

te_losses = []
te_losses_ = []
for k, (train_loader, test_loader) in enumerate(dataset.split_cross_val()):
    if k == 0:
        print('Train #batches:', len(train_loader))
        print('Test #batches:', len(test_loader))

    _start_time = time.time()
    model = EyeTrackingPredictor(initial_word_embedding.clone(),
                                 dataset.max_seq_len)
    optimizer = torch.optim.Adam(model.parameters(), lr=INITIAL_LR)
    if USE_CUDA:
        model = model.cuda()

    e_tr_losses = []
    e_tr_losses_ = []
    e_te_losses = []
    e_te_losses_ = []
    for e in range(NUM_EPOCHS):
        train_loss, train_loss_ = iterate(train_loader)
        test_loss, test_loss_ = iterate(test_loader, train=False)
        e_tr_losses.append(train_loss)
        e_tr_losses_.append(train_loss_)
        e_te_losses.append(test_loss)
        e_te_losses_.append(test_loss_)

        print('k:', k, 'e:', e,
              '{:.5f}'.format(train_loss), '{:.5f}'.format(test_loss))
        # print(train_loss_)
        # print(test_loss_)

    best_epoch = np.argmin(e_te_losses)
    te_losses.append(e_te_losses[best_epoch])
    te_losses_.append(e_te_losses_[best_epoch])
    print(k, '[e={}] '.format(best_epoch),
          '- Train rMSE: {:.5f}'.format(e_tr_losses[best_epoch]),
          'Test rMSE: {:.5f} '.format(e_te_losses[best_epoch]),
          '({:.2f}s)'.format(time.time() - _start_time))
    print('Train MSE_:', e_tr_losses_[best_epoch])
    print('Test MSE_:', e_te_losses_[best_epoch])

print('\nCV Mean Test Loss:', np.mean(te_losses))
print(torch.stack(te_losses_).mean(0))
