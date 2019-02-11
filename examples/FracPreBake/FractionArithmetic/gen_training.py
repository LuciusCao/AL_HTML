import argparse
import csv
import json
from operator import itemgetter
from os import listdir
from os.path import join as join_path
from isomorphic import gen_iso_brds


def parse_file(filename):
    with open(filename) as f:
        reader = csv.DictReader(f, delimiter='\t')
        return [r for r in reader]


def get_problem_orders(transactions):
    data = [r for r in transactions]

    # This comes from never trusting the order of a datashop transaction file
    # but its probably unnecessary
    data.sort(key=itemgetter('Anon Student Id', 'Time'))
    subset = {}

    for d in data:
        k = (d['Anon Student Id'], d['Problem Name'])
        subset[k] = d
    data = [subset[k] for k in subset]
    data.sort(key=itemgetter('Anon Student Id', 'Time'))

    sequences = {}
    for d in data:
        if d['Anon Student Id'] not in sequences:
            sequences[d['Anon Student Id']] = []
            if len(sequences) > 10:
                break
        if d['Level (ProblemSet)'].lower() in ('pretest', 'midtest a',
                                               'midtest b', 'posttest',
                                               'dposttest'):
            continue
        if d['Problem Name'][0] == 'M':
            # TODO - does this break?
            d['Problem Name'] = 'M' + d['Problem Name'][2:]
        if d['Problem Name'][0] == 'T' or \
           d['Problem Name'] == 'InstructionSlide':
            continue
        sequences[d['Anon Student Id']].append(d['Problem Name'])
    return sequences


def gen_training(transactions,
                 agent_type="WhereWhenHowNoFoa",
                 output_root="out",
                 problem_brds='converted_brds/',
                 problem_html="FractionArithmetic/HTML/fraction_arithmetic.html",
                 prepost_brds="mass_production/mass_production_brds/",
                 prepost_html="mass_production/HTML/pretest.html",
                 num_pretest=8,
                 iso_brds="iso"):

    sequences = get_problem_orders(transactions)

    control = [{'agent_name': 'Control_' + agent,
                'agent_type': agent_type,

                "stay_active": True, 
                "dont_save": True, 
                "args" : {
                    "when_learner": "trestle",
                    "where_learner": "MostSpecific" 
                },

                # 'output_dir': join_path(output_root, 'control', agent),
                'problem_set':
                    [{"set_params": {"HTML": problem_html,
                                     "examples_only": False}}] +
                    [{'question_file': join_path(problem_brds, prob + '.brd')}
                     for prob in sequences[agent]]}
               for agent in sequences]

    control = {'training_set1': control}
    with open('control_training.json', 'w') as out:
        json.dump(control, out)

    pre_test = [{'agent_name': 'Pretest_' + agent,
                 'agent_type': agent_type,

                "stay_active": True, 
                "dont_save": True, 
                "args" : {
                    "when_learner": "trestle",
                    "where_learner": "MostSpecific" 
                },

                 # 'output_dir': join_path(output_root, 'pretest', agent),
                 'problem_set':
                     [{"set_params": {"HTML": prepost_html,
                                      "examples_only": True}}] +
                     [{'question_file': join_path(prepost_brds,
                                                  '_'.join((agent, 'Pretest',
                                                           str(i + 1))))}
                      for i in range(num_pretest)] +
                     [{"set_params": {"HTML": problem_html,
                                      "examples_only": False}}] +
                     [{'question_file': join_path(problem_brds, prob + '.brd')}
                      for prob in sequences[agent]]}
                for agent in sequences]
    pre_test = {'training_set1': pre_test}
    with open('pretest_training.json', 'w') as out:
        json.dump(pre_test, out)


    isomorphic = [{'agent_name': 'Iso_' + agent,
                 'agent_type': agent_type,

                "stay_active": True, 
                "dont_save": True, 
                "args" : {
                    "when_learner": "trestle",
                    "where_learner": "MostSpecific" 
                },

                 # 'output_dir': join_path(output_root, 'pretest', agent),
                 'problem_set':
                     [{"set_params": {"HTML": problem_html,
                                      "examples_only": True}}] +
                     [{'question_file': join_path(iso_brds, agent, 'brds', n)}
                      for n in listdir(join_path(iso_brds, agent, 'brds'))] +
                     [{"set_params": {"HTML": problem_html,
                                      "examples_only": False}}] +
                     [{'question_file': join_path(problem_brds, prob + '.brd')}
                      for prob in sequences[agent]]}
                for agent in sequences]
    isomorphic = {'training_set1': pre_test}
    with open('iso_training.json', 'w') as out:
        json.dump(isomorphic, out)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='A utility to generate training jsons based on datashop'
                    'transaction files.')
    parser.add_argument('-trans_file',
                        help="The datashop transaction file to use.")
    parser.add_argument('-agent_type',
                        choices=['WhereWhenHowNoFoa', 'RLAgent'],
                        default='WhereWhenHowNoFoa',
                        help="The type of agent to set in the training.json")
    parser.add_argument('-output_root',
                        default='out',
                        help="The root directory to use for output_dir in the"
                             "agent specfications.")
    parser.add_argument('-problem_brds',
                        default='converted_brds/',
                        help="The directory location of the brd files for the"
                             "standard problem set.")
    parser.add_argument('-problem_html',
                        default='FractionArithmetic/HTML/fraction_arithmetic.html',
                        help="The HTML file to use for the standard problems.")
    parser.add_argument('-prepost_brds',
                        default='mass_production/mass_production_brds/',
                        help="The directory location of the individualized "
                             "pre-post test brds")
    parser.add_argument('-prepost_html',
                        default='mass_production/HTML/pretest.html',
                        help="The HTML file to use for the pre-post problems.")
    parser.add_argument('-num_pretest',
                        type=int,
                        default=8,
                        help="The number of pretest items to add to the"
                             "burn-in training")
    parser.add_argument('-subset_brds',
                        default='IntegerArithmetic/brds/',
                        help="The directory location of the brds for the"
                             "relevant substep problems. I don't currently use"
                             "this yet.")
    parser.add_argument('-subset_html',
                        default='IntegerArithmetic/HTML/IntegerArithmetic.html',
                        help="The HTML file to use for the relevant substep"
                             "problems. I don't currently use this yet.")

    parser.add_argument('-model_file',
                        help="The datashop model value file to use.")
    parser.add_argument('-iso_brds',
                        default='iso/',
                        help="The directory location of brds for pik problems for each student.")
    parser.add_argument('-mass_production_templates',
                        default='mass_production/',
                        help="The directory location of AS, AD, and M brd templates.")

    args = parser.parse_args()
    data = parse_file(args.trans_file)

    gen_iso_brds(args.model_file, args.iso_brds, args.mass_production_templates)
    gen_training(data,
                 agent_type=args.agent_type,
                 output_root=args.output_root,
                 problem_brds=args.problem_brds,
                 problem_html=args.problem_html,
                 prepost_brds=args.prepost_brds,
                 prepost_html=args.prepost_html,
                 num_pretest=args.num_pretest,
                 iso_brds=args.iso_brds
    )

