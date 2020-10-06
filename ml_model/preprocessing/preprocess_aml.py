"""
Copyright (C) Microsoft Corporation. All rights reserved.​
 ​
Microsoft Corporation (“Microsoft”) grants you a nonexclusive, perpetual,
royalty-free right to use, copy, and modify the software code provided by us
("Software Code"). You may not sublicense the Software Code or any use of it
(except to your affiliates and to vendors to perform work on your behalf)
through distribution, network access, service agreement, lease, rental, or
otherwise. This license does not purport to express any claim of ownership over
data you may have shared with Microsoft in the creation of the Software Code.
Unless applicable law gives you more rights, Microsoft reserves all other
rights not expressly granted herein, whether by implication, estoppel or
otherwise. ​
 ​
THE SOFTWARE CODE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
MICROSOFT OR ITS LICENSORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER
IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THE SOFTWARE CODE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
"""
from azureml.core.run import Run
import argparse
import json
from preprocess_images import resize_images
from util.model_helper import get_or_register_dataset, get_aml_context


def main():
    print("Running preprocess.py")

    parser = argparse.ArgumentParser("preprocess")
    parser.add_argument(
        "--dataset_name",
        type=str,
        help=("Dataset name. Dataset must be passed by name\
              to always get the desired dataset version\
              rather than the one used while the pipeline creation")
    )

    parser.add_argument(
        "--datastore_name",
        type=str,
        help=("Datastore name. If none, use the default datastore")
    )

    parser.add_argument(
        "--data_file_path",
        type=str,
        help=("data file path, if specified,\
               a new version of the dataset will be registered")
    )

    parser.add_argument(
        "--caller_run_id",
        type=str,
        help=("caller run id, for example ADF pipeline run id")
    )

    parser.add_argument(
        "--step_output",
        type=str,
        help=("output of processed data")
    )

    args = parser.parse_args()

    print("Argument [dataset_name]: %s" % args.dataset_name)
    print("Argument [datastore_name]: %s" % args.datastore_name)
    print("Argument [data_file_path]: %s" % args.data_file_path)
    print("Argument [caller_run_id]: %s" % args.caller_run_id)
    print("Argument [step_output]: %s" % args.step_output)

    data_file_path = args.data_file_path
    dataset_name = args.dataset_name
    datastore_name = args.datastore_name
    output_path = args.step_output

    run = Run.get_context()

    # Get Azure machine learning workspace
    aml_workspace, *_ = get_aml_context(run)

    # Get the dataset
    dataset = get_or_register_dataset(
        dataset_name,
        datastore_name,
        data_file_path,
        aml_workspace)

    # Load the training parameters from the parameters file
    print("Getting preprocessing parameters")
    with open("parameters.json") as f:
        pars = json.load(f)
    try:
        preprocessing_args = pars["preprocessing"]
    except KeyError:
        print("Could not load preprocessing values from file")
        preprocessing_args = {}

    # Log the training parameters
    print(f"Parameters: {preprocessing_args}")
    for (k, v) in preprocessing_args.items():
        run.log(k, v)
        run.parent.log(k, v)

    # Link dataset to the step run so it is trackable in the UI
    run.input_datasets['input_dataset'] = dataset
    run.parent.tag("dataset_id", value=dataset.id)

    # Process data
    mount_context = dataset.mount()
    mount_context.start()
    print(f"mount_point is: {mount_context.mount_point}")
    resize_images(mount_context.mount_point, output_path, preprocessing_args)
    mount_context.stop()

    run.tag("run_type", value="preprocess")
    print(f"tags now present for run: {run.tags}")

    run.complete()


if __name__ == '__main__':
    main()
