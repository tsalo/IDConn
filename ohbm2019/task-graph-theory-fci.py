import numpy as np
import pandas as pd
from os import makedirs
from os.path import join, exists
from nilearn.input_data import NiftiLabelsMasker
from nilearn.connectome import ConnectivityMeasure
from nilearn.plotting import plot_anat, plot_roi
import bct
import datetime

subjects = ['101', '102', '103', '104', '106', '107', '108', '110', '212', '213',
            '214', '215', '216', '217', '218', '219', '320', '321', '322', '323',
            '324', '325', '327', '328', '329', '330', '331', '332', '333', '334',
            '335', '336', '337', '338', '339', '340', '341', '342', '343', '344',
            '345', '346', '347', '348', '349', '350', '451', '452', '453', '455',
            '456', '457', '458', '459', '460', '462', '463', '464', '465', '467',
            '468', '469', '470', '502', '503', '571', '572', '573', '574', '575',
            '577', '578', '579', '580', '581', '582', '584', '585', '586', '587',
            '588', '589', '590', '591', '592', '593', '594', '595', '596', '597',
            '598', '604', '605', '606', '607', '608', '609', '610', '611', '612',
            '613', '614', '615', '616', '617', '618', '619', '620', '621', '622',
            '623', '624', '625', '626', '627', '628', '629', '630', '631', '633',
            '634']
#subjects = ['101', '102']
kappa_upper = 0.21
kappa_lower = 0.31

data_dir = '/home/data/nbc/physics-learning/data/pre-processed/'
sink_dir = '/home/data/nbc/physics-learning/retrieval-graphtheory/output'

shen = '/home/kbott006/physics-retrieval/shen2015_2mm_268_parcellation.nii.gz'
craddock = '/home/kbott006/physics-retrieval/craddock2012_tcorr05_2level_270_2mm.nii.gz'
masks = ['shen2015', 'craddock2012']

tasks = {'fci': [{'conditions': ['Physics', 'NonPhysics']},
                  {'runs': [0,1,2]}],}


sessions = [0,1]
sesh = ['pre', 'post']
conds = ['high-level', 'lower-level']

lab_notebook_dir = '/home/kbott006/lab_notebook/'
index = pd.MultiIndex.from_product([subjects, sessions, tasks, conds, masks], names=['subject', 'session', 'task', 'condition', 'mask'])
lab_notebook = pd.DataFrame(index=index, columns=['start', 'end', 'errors'])

correlation_measure = ConnectivityMeasure(kind='correlation')

index = pd.MultiIndex.from_product([subjects, sessions, tasks, conds, masks], names=['subject', 'session', 'task', 'condition', 'mask'])

df = pd.DataFrame(columns=['efficiency', 'charpath', 'modularity'], index=index, dtype=np.float64)

for subject in subjects:
    for session in sessions:

        for task in tasks.keys():
            for i in np.arange(0, len(tasks[task][0]['conditions'])):
                conditions = tasks[task][0]['conditions']
                for mask in masks:
                    try:
                        lab_notebook.at[(subject, session, task, conds[i], mask),'start'] = str(datetime.datetime.now())
                        corrmat = np.genfromtxt(join(sink_dir, sesh[session], subject, '{0}-session-{1}_{2}-{3}_{4}-corrmat.csv'.format(subject, session, task, conditions[i], mask)), delimiter=' ')

                        ge_s = []
                        cp_s = []
                        md_s = []
                        for p in np.arange(kappa_upper, kappa_lower, 0.01):
                            ntwk = []
                            thresh = bct.threshold_proportional(corrmat, p, copy=True)

                            #network measures of interest here
                            #global efficiency
                            ge = bct.efficiency_wei(thresh)
                            ge_s.append(ge)

                            #characteristic path length
                            cp = bct.charpath(thresh)
                            cp_s.append(cp[0])

                            #modularity
                            md = bct.modularity_louvain_und(thresh)
                            md_s.append(md[1])

                        df.at[(subject, session, task, conds[i], mask), 'efficiency'] = np.trapz(ge_s, dx=0.01)
                        df.at[(subject, session, task, conds[i], mask), 'charpath'] = np.trapz(cp_s, dx=0.01)
                        df.at[(subject, session, task, conds[i], mask), 'modularity'] = np.trapz(md_s, dx=0.01)

                        #df.to_csv(join(sink_dir, 'resting-state_graphtheory_shen+craddock.csv'), sep=',')
                        lab_notebook.at[(subject, session, task, conds[i], mask),'end'] = str(datetime.datetime.now())
                    except Exception as e:
                        print(e, subject, session)
                        lab_notebook.at[(subject, session, task, conds[i], mask),'errors'] = [e, str(datetime.datetime.now())]
                    df.to_csv(join(sink_dir, 'physics-learning-tasks_graphtheory_shen+craddock.csv'), sep=',')

df.to_csv(join(sink_dir, 'physics-learning-fci_graphtheory_shen+craddock.csv_{0}.csv'.format(str(datetime.datetime.today()))), sep=',')
lab_notebook.to_csv(join(lab_notebook_dir, 'physics-learning-fci-graphtheory_{0}.csv'.format(str(datetime.datetime.now()))))
