import numpy as np
import pandas as pd
from os.path import join, exists
import bct
import datetime

def avg_corrmat(layout, task, session):
    subjects = layout.get_subjects(task=task,session=session)
    corrmats = {}
    for subject in subjects:
        try:
            if task == "rest":
                corrmat = np.genfromtxt(
                    join(
                        data_dir,
                        sesh[session],
                        subject,
                        "{0}-session-{1}-{2}_network_corrmat_{3}.csv".format(
                            subject, session, task, atlas
                        ),
                    ),
                    delimiter=",",
                )
            else:
                corrmat = np.genfromtxt(
                    join(
                        data_dir,
                        sesh[session],
                        subject,
                        "{0}-session-{1}_{2}-{3}_{4}-corrmat.csv".format(
                            subject, session, task, condition, atlas
                        ),
                    ),
                    delimiter=" ",
                )
            # corrmat = np.genfromtxt(join(data_dir, '{0}-session-{1}_{2}-{3}_{4}-corrmat.csv'.format(subject, session, task, condition, atlas)), delimiter=' ')
            corrmats[subject] = corrmat
        except Exception as e:
            print(subject, e)
    data = list(corrmats.values())
    stacked_corrmats = np.array(data)
    print('Stacked corrmats have dimensions', stacked_corrmats.shape)
    avg_corrmat = np.mean(stacked_corrmats, axis=0)
    return avg_corrmat


def null_model_und_sign(W, bin_swaps=5, wei_freq=0.1, seed=None):
    def get_rng(seed):
        if seed is None or seed == np.random:
            return np.random.mtrand._rand
        elif isinstance(seed, np.random.RandomState):
            return seed
        try:
            rstate = np.random.RandomState(seed)
        except ValueError:
            rstate = np.random.RandomState(random.Random(seed).randint(0, 2 ** 32 - 1))
        return rstate

    def randmio_und_signed(R, itr, seed=None):
        rng = get_rng(seed)
        R = R.copy()
        n = len(R)

        itr *= int(n * (n - 1) / 2)

        max_attempts = int(np.round(n / 2))
        eff = 0

        for it in range(int(itr)):
            att = 0
            while att <= max_attempts:

                a, b, c, d = pick_four_unique_nodes_quickly(n, rng)

                r0_ab = R[a, b]
                r0_cd = R[c, d]
                r0_ad = R[a, d]
                r0_cb = R[c, b]

                # rewiring condition
                if (
                    np.sign(r0_ab) == np.sign(r0_cd)
                    and np.sign(r0_ad) == np.sign(r0_cb)
                    and np.sign(r0_ab) != np.sign(r0_ad)
                ):

                    R[a, d] = R[d, a] = r0_ab
                    R[a, b] = R[b, a] = r0_ad

                    R[c, b] = R[b, c] = r0_cd
                    R[c, d] = R[d, c] = r0_cb

                    eff += 1
                    break

                att += 1

        return R, eff

    def pick_four_unique_nodes_quickly(n, seed=None):
        """
        This is equivalent to np.random.choice(n, 4, replace=False)
        Another fellow suggested np.random.random_sample(n).argpartition(4) which is
        clever but still substantially slower.
        """
        rng = get_rng(seed)
        k = rng.randint(n ** 4)
        a = k % n
        b = k // n % n
        c = k // n ** 2 % n
        d = k // n ** 3 % n
        if a != b and a != c and a != d and b != c and b != d and c != d:
            return (a, b, c, d)
        else:
            # the probability of finding a wrong configuration is extremely low
            # unless for extremely small n. if n is extremely small the
            # computational demand is not a problem.

            # In my profiling it only took 0.4 seconds to include the uniqueness
            # check in 1 million runs of this function so I think it is OK.
            return pick_four_unique_nodes_quickly(n, rng)

    rng = get_rng(seed)
    if not np.allclose(W, W.T):
        print("Input must be undirected")
    W = W.copy()
    n = len(W)
    np.fill_diagonal(W, 0)  # clear diagonal
    Ap = W > 0  # positive adjmat
    An = W < 0  # negative adjmat

    if np.size(np.where(Ap.flat)) < (n * (n - 1)):
        W_r, eff = randmio_und_signed(W, bin_swaps, seed=rng)
        Ap_r = W_r > 0
        An_r = W_r < 0
    else:
        Ap_r = Ap
        An_r = An

    W0 = np.zeros((n, n))
    for s in (1, -1):
        if s == 1:
            Acur = Ap
            A_rcur = Ap_r
        else:
            Acur = An
            A_rcur = An_r

        S = np.sum(W * Acur, axis=0)  # strengths
        Wv = np.sort(W[np.where(np.triu(Acur))])  # sorted weights vector
        i, j = np.where(np.triu(A_rcur))
        (Lij,) = np.where(np.triu(A_rcur).flat)  # weights indices

        P = np.outer(S, S)

        if wei_freq == 0:  # get indices of Lij that sort P
            Oind = np.argsort(P.flat[Lij])  # assign corresponding sorted
            W0.flat[Lij[Oind]] = s * Wv  # weight at this index
        else:
            wsize = np.size(Wv)
            wei_period = np.round(1 / wei_freq).astype(
                int
            )  # convert frequency to period
            lq = np.arange(wsize, 0, -wei_period, dtype=int)
            for m in lq:  # iteratively explore at this period
                # get indices of Lij that sort P
                Oind = np.argsort(P.flat[Lij])
                R = rng.permutation(m)[: np.min((m, wei_period))]
                for q, r in enumerate(R):
                    # choose random index of sorted expected weight
                    o = Oind[r]
                    W0.flat[Lij[o]] = s * Wv[r]  # assign corresponding weight

                    # readjust expected weighted probability for i[o],j[o]
                    f = 1 - Wv[r] / S[i[o]]
                    P[i[o], :] *= f
                    P[:, i[o]] *= f
                    f = 1 - Wv[r] / S[j[o]]
                    P[j[o], :] *= f
                    P[:, j[o]] *= f

                    # readjust strength of i[o]
                    S[i[o]] -= Wv[r]
                    # readjust strength of j[o]
                    S[j[o]] -= Wv[r]

                O = Oind[R]
                # remove current indices from further consideration
                Lij = np.delete(Lij, O)
                i = np.delete(i, O)
                j = np.delete(j, O)
                Wv = np.delete(Wv, R)

    W0 = W0 + W0.T
    return W0

def generate_null(layout, task, session, mask):
    null_dist = pd.DataFrame(index=subjects, columns=["mean", "sdev"])
    avg_corr = avg_corrmat(
        layout, task, session, mask
    )
    eff_perm = []
    j = 1
    while j < 3:
        effs = []
        W = null_model_und_sign(avg_corr.values)
        for thresh in np.arange(0.21, 0.31, 0.03):
            thresh_corr = bct.threshold_proportional(W, thresh)
            leff = bct.efficiency_wei(thresh_corr)
            effs.append(leff)
        effs_arr = np.asarray(effs)
        leff_auc = np.trapz(effs_arr, dx=0.03, axis=0)
        eff_perm.append(leff_auc)
        j += 1
    null_dist.at[(sesh[session], task, conds[i], mask), "mean"] = np.mean(
        eff_perm
    )
    null_dist.at[(sesh[session], task, conds[i], mask), "sdev"] = np.std(
        eff_perm
    )
    return null_dist