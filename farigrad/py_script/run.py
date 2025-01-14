import torch
from torch import nn
from fairgrad.torch import FairnessLoss
import numpy as np
import support_based as spb
import support_dataset as spd
import support_net as spn
import os
import pickle


def run_model(da_tr, attri_str, lab_ind, model_num, bat_num, ep, tr_it, te_it, pr_it, le_rate=0.0005):
    # create folder
    sa_str = spb.com_mul_str([da_tr, attri_str, lab_ind, model_num, bat_num, ep, tr_it, te_it])
    sa_fo = spb.mo_pa + 'save_results/' + sa_str + '/'
    os.mkdir(sa_fo)

    # create datase
    da = spd.dataset(da_tr, attri_str, bat_num, lab_ind)

    # device
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using {device} device")

    # construct the network
    model = spn.get_model(2, model_num)
    model.to(device)
    transforms = spn.get_transforms()
    transforms.to(device)

    fairness_function = "equal_odds"
    loss_fn = FairnessLoss(
        base_loss_class=nn.CrossEntropyLoss,
        class_weights=da.class_weights,
        y_train=da.y,
        s_train=da.s,
        fairness_measure=fairness_function,
    )
    loss_fn.to(device)

    optimizer = torch.optim.SGD(model.parameters(), lr=le_rate)

    # train
    res = [[], [], []]
    for i in range(ep):

        if spb.check(res, 4):
            le_rate = le_rate/2
            optimizer.param_groups[0]['lr'] = le_rate

        tr_los = spn.train(da, model, transforms, loss_fn, optimizer, device, tr_it, pr_it)

        # validation
        va_loss, va_pred, va_id, va_met = spn.test(da, model, transforms, loss_fn, 'va', device, te_it, pr_it)
        print('all_validation', i, va_loss, va_met)

        # test
        te_loss, te_pred, te_id, te_met = spn.test(da, model, transforms, loss_fn, 'te', device, te_it, pr_it)
        print('all_test', i, te_loss, te_met)

        # add
        res[0].append([tr_los])
        res[1].append([va_loss, va_pred, va_id, va_met])
        res[2].append([te_loss, te_pred, te_id, te_met])

        # save the result
        with open(sa_fo + 'res.txt', 'wb') as fi:
            pickle.dump(res, fi)

        # save the model
        torch.save(model.state_dict(), sa_fo + 'model_weights.pth')

        # whether stop:
        if spb.check(res, 100):
            break

    return


