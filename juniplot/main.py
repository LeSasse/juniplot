"""Make some plots from junifer output for initial inspection."""

from argparse import ArgumentParser
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from joblib import Parallel, delayed
from junifer.storage import HDF5FeatureStorage
from nilearn.connectome import sym_matrix_to_vec, vec_to_sym_matrix


def parse_args():
    """Parse arguments."""
    parser = ArgumentParser(
        description="Make some plots from junifer output for initial inspection."
    )
    parser.add_argument(
        "HDF5", help="Path to HDF5 file junifer output.", type=Path
    )
    parser.add_argument(
        "output", help="Path to store output plots.", type=Path
    )
    parser.add_argument(
        "-c",
        "--cmap",
        help=(
            "Matplotlib colormap, see: "
            "https://matplotlib.org/stable/gallery/color/colormap_reference.html"
        ),
        default="coolwarm",
    )
    parser.add_argument("-s", "--single-output", action="store_true")
    parser.add_argument(
        "-f",
        "--format",
        help="Format to save output figures.",
        choices=["pdf", "png", "svg"],
        default="png",
    )
    parser.add_argument(
        "-n",
        "--n-jobs",
        help=(
            "juniplot can plot different markers in parallel, so you can "
            "specify the number of jobs to run in parallel here."
        ),
        type=int,
        default=1,
    )
    parser.add_argument("-a", "--average-only", action="store_true")

    return parser.parse_args()


def get_fc_markers(feature_storage):
    """Return a list of marker dictionaries containing the marker metadata."""
    markers = []
    for feature_md5, feature in feature_storage.list_features().items():
        if "FunctionalConnectivity" in feature["marker"]["class"]:
            markers.append(feature)

    return markers


def plot_one_sub(subject, outpath, cmap, outformat):
    """Plot one subjects FC matrix from the vectorised representation."""
    cm = 1 / 2.54
    fig = plt.figure(figsize=(18 * cm, 8 * cm))
    grid = fig.add_gridspec(1, 2)

    matrix = np.squeeze(vec_to_sym_matrix(subject))
    np.fill_diagonal(matrix, 1)

    ax_a = fig.add_subplot(grid[0, 0])
    hmap = sns.heatmap(matrix, vmin=-1, vmax=1, cmap=cmap, ax=ax_a)

    ax_a = fig.add_subplot(grid[0, 1])
    hist = sns.histplot(sym_matrix_to_vec(matrix))
    hist.set(xlim=(-1, 1))

    plt.tight_layout()

    if isinstance(subject.name, str):
        filename = f"{subject.name}.{outformat}"
    else:
        filename = "_".join(subject.name) + f".{outformat}"

    outfile = outpath / filename

    sns.despine(fig)
    fig.savefig(outfile)
    plt.close()


def plot_one_marker(
    feature_storage,
    marker,
    output_path,
    cmap,
    outformat,
    grp_average,
    average_only,
):
    """Plot a set of subjects for one marker."""
    marker_out = output_path / marker["name"]
    marker_out.mkdir(exist_ok=True)
    marker_df = feature_storage.read_df(marker["name"])

    if not average_only:
        marker_df.apply(
            plot_one_sub,
            axis=1,
            outpath=marker_out,
            cmap=cmap,
            outformat=outformat,
        )

    if grp_average or average_only:
        # plot the group average after r-to-z and z-to-r transform
        averaged = marker_df.apply(np.arctanh, axis=1).mean().apply(np.tanh)
        averaged.name = "group_average"
        plot_one_sub(
            averaged,
            outpath=marker_out,
            cmap=cmap,
            outformat=outformat,
        )


def plot_fc_markers(
    feature_storage,
    fc_markers,
    output_path,
    cmap,
    outformat,
    grp_average,
    average_only,
    n_jobs,
):
    """Plot the markers in parallel."""
    Parallel(n_jobs=n_jobs)(
        delayed(plot_one_marker)(
            feature_storage,
            marker,
            output_path,
            cmap,
            outformat,
            grp_average,
            average_only,
        )
        for marker in fc_markers
    )


def main():
    """Enter the main program."""
    args = parse_args()
    feature_storage = HDF5FeatureStorage(
        args.HDF5, single_output=args.single_output
    )
    fc_markers = get_fc_markers(feature_storage)

    if not args.output.is_dir():
        raise ValueError("Output directory does not exist.")

    plot_fc_markers(
        feature_storage,
        fc_markers,
        args.output,
        cmap=args.cmap,
        outformat=args.format,
        grp_average=not args.single_output,
        average_only=args.average_only,
        n_jobs=args.n_jobs,
    )


if __name__ == "__main__":
    main()
