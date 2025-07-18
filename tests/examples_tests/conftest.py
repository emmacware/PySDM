# pylint: disable=missing-module-docstring
import os
import pathlib
import re


# https://stackoverflow.com/questions/7012921/recursive-grep-using-python
def findfiles(path, regex):
    reg_obj = re.compile(regex)
    res = []
    for root, _, fnames in os.walk(path):
        for fname in fnames:
            if reg_obj.match(fname):
                res.append(os.path.join(root, fname))
    return res


TEST_SUITES = {
    "chemistry_extraterrestrial": [
        "Jaruga_and_Pawlowska_2018",
        "Kreidenweis_et_al_2003",
        "Toon_et_al_1980",
    ],
    "freezing": [
        "Alpert_and_Knopf_2016",
        "Ervens_and_Feingold_2012",
        "Niedermeier_et_al_2014",
        "Spichtinger_et_al_2023",
    ],
    "isotopes": [
        "Bolot_et_al_2013",
        "Merlivat_and_Nief_1967",
        "Van_Hook_1968",
        "Pierchala_et_al_2022",
        "Gedzelman_and_Arnold_1994",
        "Graf_et_al_2019",
        "Lamb_et_al_2017",
        "Miyake_et_al_1968",
        "Rozanski_and_Sonntag_1982",
        "Bolin_1958",
        "Stewart_1975",
        "Kinzer_And_Gunn_1951",
        "Pruppacher_and_Rasmussen_1979",
        "Fisher_1991",
        "Jouzel_and_Merlivat_1984",
    ],
    "condensation_a": [
        "Lowe_et_al_2019",
        "Singer_Ward",
        "Rogers_1975",
    ],
    "condensation_b": [
        "Abdul_Razzak_Ghan_2000",
        "Arabas_and_Shima_2017",
        "Pyrcel",
        "Yang_et_al_2018",
    ],
    "condensation_c": [
        "Grabowski_and_Pawlowska_2023",
        "Jensen_and_Nugent_2017",
        "Abade_and_Albuquerque_2024",
    ],
    "coagulation": ["Berry_1967", "Shima_et_al_2009"],
    "breakup": ["Bieli_et_al_2022", "deJong_Mackay_et_al_2023", "Srivastava_1982"],
    "multi-process_a": [
        "Arabas_et_al_2015",
        "_HOWTOs",
    ],
    "multi-process_b": [
        "Arabas_et_al_2025",
    ],
    "multi-process_c": [
        "Bartman_2020_MasterThesis",
    ],
    "multi-process_d": [
        "Bartman_et_al_2021",
    ],
    "multi-process_e": [
        "deJong_Azimi",
        "Bulenok_2023_MasterThesis",
        "Morrison_and_Grabowski_2007",
        "Shipway_and_Hill_2012",
        "seeding",
        "utils",
        "Zaba_et_al_2025",
        "Gonfiantini_1986",
    ],
}


def get_selected_test_paths(suite_name, paths):
    if suite_name is None:
        return paths

    cases = TEST_SUITES[suite_name]

    result = []
    for path in paths:
        for case in cases:
            path = pathlib.Path(path)
            if case in path.parts:
                result.append(path)

    return result


def pytest_addoption(parser):
    parser.addoption("--suite", action="store")


def pytest_generate_tests(metafunc):
    suite_name = metafunc.config.option.suite

    pysdm_examples_abs_path = (
        pathlib.Path(__file__)
        .parent.parent.parent.absolute()
        .joinpath("examples")
        .joinpath("PySDM_examples")
    )
    if "notebook_filename" in metafunc.fixturenames:
        notebook_paths = findfiles(pysdm_examples_abs_path, r".*\.(ipynb)$")
        selected_paths = get_selected_test_paths(suite_name, notebook_paths)
        metafunc.parametrize(
            "notebook_filename",
            selected_paths,
            ids=[str(path) for path in selected_paths],
        )

    if "example_filename" in metafunc.fixturenames:
        examples_paths = findfiles(
            pysdm_examples_abs_path,
            r".*\.(py)$",
        )
        selected_paths = get_selected_test_paths(suite_name, examples_paths)
        metafunc.parametrize(
            "example_filename",
            selected_paths,
            ids=[str(path) for path in selected_paths],
        )
