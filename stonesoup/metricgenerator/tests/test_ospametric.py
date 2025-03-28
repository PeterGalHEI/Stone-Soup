"""GOSPA/OSPA tests."""
import datetime

import numpy as np
import pytest

from ..manager import MultiManager
from ..ospametric import GOSPAMetric, OSPAMetric, _SwitchingLoss
from ...types.detection import Detection
from ...types.groundtruth import GroundTruthPath, GroundTruthState
from ...types.state import State, ParticleState
from ...types.track import Track


def test_gospametric_extractstates():
    """Test GOSPA extract states."""
    generator = GOSPAMetric(
        c=10.0,
        p=1
    )
    # Test state extraction
    time_start = datetime.datetime.now()
    detections = [Detection(state_vector=np.array([[i]]), timestamp=time_start)
                  for i in range(5)]
    tracks = {Track(states=[State(state_vector=[[i]],
                                  timestamp=time_start)]) for i in range(5)}
    truths = {GroundTruthPath(states=[GroundTruthState(state_vector=[[i]],
                                                       timestamp=time_start)])
              for i in range(5)}
    det_states = generator.extract_states(detections)
    assert det_states.states == detections
    track_states = generator.extract_states(tracks)
    assert set(track_states) == set(t.states[0] for t in tracks)
    truth_states = generator.extract_states(truths)
    assert set(truth_states) == set(t.states[0] for t in truths)


@pytest.mark.parametrize('num_states', (2, 5))
def test_gospametric_compute_assignments(num_states):
    """Test GOSPA assignment algorithm."""
    generator = GOSPAMetric(
        c=10.0,
        p=1
    )
    time_now = datetime.datetime.now()
    track_obj = Track([State(state_vector=[[i]], timestamp=time_now)
                      for i in range(num_states)])
    truth_obj = GroundTruthPath([State(state_vector=[[i]], timestamp=time_now)
                                for i in range(num_states)])
    cost_matrix = generator.compute_cost_matrix(track_obj.states,
                                                truth_obj.states)
    neg_cost_matrix = -1.*cost_matrix
    meas_to_truth, truth_to_meas, opt_cost =\
        generator.compute_assignments(neg_cost_matrix)

    assert opt_cost == 0.0
    assert np.array_equal(meas_to_truth, truth_to_meas)
    assert np.array_equal(meas_to_truth,
                          np.array([i for i in range(num_states)]))

    # Missing 1 track
    cost_matrix = generator.compute_cost_matrix(track_obj.states[:-1],
                                                truth_obj.states)
    neg_cost_matrix = -1.*cost_matrix
    meas_to_truth, truth_to_meas, opt_cost = \
        generator.compute_assignments(neg_cost_matrix)

    assert opt_cost == 0.0
    assert np.array_equal(meas_to_truth, truth_to_meas[:-1])
    assert truth_to_meas[-1] == -1
    assert np.array_equal(meas_to_truth,
                          np.array([i for i in range(num_states - 1)]))

    # Missing 1 truth
    cost_matrix = generator.compute_cost_matrix(track_obj.states,
                                                truth_obj.states[:-1])
    neg_cost_matrix = -1.*cost_matrix
    meas_to_truth, truth_to_meas, opt_cost = \
        generator.compute_assignments(neg_cost_matrix)

    assert opt_cost == 0.0
    assert np.array_equal(meas_to_truth[:-1], truth_to_meas)
    assert meas_to_truth[-1] == -1
    assert np.array_equal(meas_to_truth[:-1],
                          np.array([i for i in range(num_states - 1)]))


def test_gospametric_cost_matrix():
    """Test GOSPA cost matrix. Also, indirectly checks compute distance."""
    num_states = 5
    generator = GOSPAMetric(
        c=10.0,
        p=1
    )
    time_now = datetime.datetime.now()
    track_obj = Track([State(state_vector=[[i]], timestamp=time_now)
                      for i in range(num_states)])
    truth_obj = GroundTruthPath([State(state_vector=[[i]], timestamp=time_now)
                                for i in range(num_states)])
    cost_matrix = generator.compute_cost_matrix(track_obj.states,
                                                truth_obj.states)

    tmp_vec = np.arange(num_states)
    tmp_mat = np.zeros([num_states, num_states])
    for n in range(num_states):
        tmp_mat[n, :] = np.roll(tmp_vec, n)

    tmp_upper = np.triu(tmp_mat)
    test_matrix = tmp_upper + tmp_upper.transpose()
    assert np.array_equal(cost_matrix, test_matrix)


def test_gospametric_compute_gospa_metric():
    """Test compute GOSPA metric."""
    num_states = 5
    generator = GOSPAMetric(
        c=10.0,
        p=1
    )
    time_now = datetime.datetime.now()
    track_obj = Track([State(state_vector=[[i]], timestamp=time_now)
                      for i in range(num_states)])
    truth_obj = GroundTruthPath([State(state_vector=[[i]], timestamp=time_now)
                                for i in range(num_states)])
    single_time_metric, assignment_matrix =\
        generator.compute_gospa_metric(track_obj.states,
                                       truth_obj.states)
    gospa_metric = single_time_metric.value
    assert (gospa_metric['distance'] == 0.0)
    assert (gospa_metric['localisation'] == 0.0)
    assert (gospa_metric['missed'] == 0.0)
    assert (gospa_metric['false'] == 0.0)


@pytest.mark.parametrize("state_type", [State, ParticleState])
def test_gospametric_computemetric(state_type):
    """Test GOSPA compute metric."""
    generator = GOSPAMetric(
        c=10.0,
        p=1
    )
    time = datetime.datetime.now()
    # Multiple tracks and truths present at two timesteps
    tracks = {Track(states=[state_type(state_vector=[[i + 0.5]], timestamp=time),
                            state_type(state_vector=[[i + 1]],
                                       timestamp=time + datetime.timedelta(
                                       seconds=1))])
              for i in range(5)}
    truths = {GroundTruthPath(
        states=[State(state_vector=[[i]], timestamp=time),
                GroundTruthState(state_vector=[[i]],
                                 timestamp=time + datetime.timedelta(
                                     seconds=1))])
              for i in range(5)}

    manager = MultiManager([generator])
    manager.add_data({'groundtruth_paths': truths, 'tracks': tracks})
    main_metric = generator.compute_metric(manager)

    assert main_metric.title == "GOSPA Metrics"
    assert main_metric.time_range.start_timestamp == time
    assert main_metric.time_range.end_timestamp == time + datetime.timedelta(
        seconds=1)
    first_association = [i for i in main_metric.value
                         if i.timestamp == time][0]
    assert first_association.title == "GOSPA Metric"
    assert first_association.timestamp == time
    assert first_association.generator == generator
    # In the following, distance is divided by the cardinality
    # of the set since GOSPA is not normalized.
    assert first_association.value['distance'] / 5. == 0.5
    second_association = [
        i for i in main_metric.value if
        i.timestamp == time + datetime.timedelta(seconds=1)][0]
    assert second_association.title == "GOSPA Metric"
    assert second_association.timestamp == time + datetime.timedelta(seconds=1)
    assert second_association.generator == generator
    assert second_association.value['distance'] / 5. == 1


def test_ospametric_extractstates():
    """Test OSPA metric extract states."""
    generator = OSPAMetric(
        c=10,
        p=1
    )

    # Test state extraction
    time_start = datetime.datetime.now()
    detections = [Detection(state_vector=np.array([[i]]), timestamp=time_start)
                  for i in range(5)]
    tracks = {Track(states=[State(state_vector=[[i]],
                                  timestamp=time_start)]) for i in range(5)}
    truths = {GroundTruthPath(states=[GroundTruthState(state_vector=[[i]],
                                                       timestamp=time_start)])
              for i in range(5)}

    det_states = generator.extract_states(detections)
    assert det_states.states == detections
    track_states = generator.extract_states(tracks)
    assert set(track_states) == set(t.states[0] for t in tracks)
    truth_states = generator.extract_states(truths)
    assert set(truth_states) == set(t.states[0] for t in truths)


def test_ospametric_computecostmatrix():
    """Test OSPA metric compute cost matrix."""
    generator = OSPAMetric(
        c=10,
        p=1
    )

    time = datetime.datetime.now()
    track = Track(states=[
        State(state_vector=[[i]], timestamp=time)
        for i in range(5)])
    truth = GroundTruthPath(states=[
        State(state_vector=[[i]], timestamp=time)
        for i in range(5)])

    cost_matrix = generator.compute_cost_matrix(track.states, truth.states)

    assert np.array_equal(cost_matrix, np.array([[0., 1., 2., 3., 4.],
                                                 [1., 0., 1., 2., 3.],
                                                 [2., 1., 0., 1., 2.],
                                                 [3., 2., 1., 0., 1.],
                                                 [4., 3., 2., 1., 0.]]))

    cost_matrix = generator.compute_cost_matrix(track.states, truth.states[:-1])
    assert np.array_equal(cost_matrix, np.array([[0., 1., 2., 3.],
                                                 [1., 0., 1., 2.],
                                                 [2., 1., 0., 1.],
                                                 [3., 2., 1., 0.],
                                                 [4., 3., 2., 1.]]))

    # One more track than truths
    cost_matrix = generator.compute_cost_matrix(track.states, truth.states[:-1], complete=True)
    assert np.array_equal(cost_matrix, np.array([[0., 1., 2., 3., 10.],
                                                 [1., 0., 1., 2., 10.],
                                                 [2., 1., 0., 1., 10.],
                                                 [3., 2., 1., 0., 10.],
                                                 [4., 3., 2., 1., 10.]]))


def test_ospametric_computeospadistance():
    """Test OSPA metric compute OSPA distance."""
    generator = OSPAMetric(
        c=10,
        p=1
    )

    time = datetime.datetime.now()
    track = Track(states=[
        State(state_vector=[[i]], timestamp=time)
        for i in range(5)])
    truth = GroundTruthPath(states=[
        State(state_vector=[[i + 0.5]], timestamp=time)
        for i in range(5)])

    metric = generator.compute_OSPA_distance(track.states, truth.states)

    assert metric.title == "OSPA distance"
    assert metric.value == 0.5
    assert metric.timestamp == time
    assert metric.generator == generator


@pytest.mark.parametrize('p', (1, 2, np.inf), ids=('p=1', 'p=2', 'p=inf'))
def test_ospametric_computemetric(p):
    """Test OSPA compute metric."""
    generator = OSPAMetric(
        c=10,
        p=p
    )

    time = datetime.datetime.now()
    # Multiple tracks and truths present at two timesteps
    tracks = {Track(states=[State(state_vector=[[i + 0.5]], timestamp=time),
                            State(state_vector=[[i + 1.2]],
                                  timestamp=time + datetime.timedelta(
                                     seconds=1))])
              for i in range(5)}
    truths = {GroundTruthPath(
        states=[GroundTruthState(state_vector=[[i]], timestamp=time),
                GroundTruthState(state_vector=[[i + 1]],
                                 timestamp=time+datetime.timedelta(
                                     seconds=1))])
              for i in range(5)}

    manager = MultiManager([generator])
    manager.add_data({'groundtruth_paths': truths, 'tracks': tracks})
    main_metric = generator.compute_metric(manager)
    first_association, second_association = main_metric.value

    assert main_metric.title == "OSPA distances"
    assert main_metric.time_range.start_timestamp == time
    assert main_metric.time_range.end_timestamp == time + datetime.timedelta(
        seconds=1)

    assert first_association.title == "OSPA distance"
    assert first_association.value == pytest.approx(0.5)
    assert first_association.timestamp == time
    assert first_association.generator == generator

    assert second_association.title == "OSPA distance"
    assert second_association.value == pytest.approx(0.2)
    assert second_association.timestamp == time + datetime.timedelta(seconds=1)
    assert second_association.generator == generator


def test_switching_gospametric_computemetric():
    """Test GOSPA compute metric."""
    max_penalty = 2
    switching_penalty = 3
    p = 2
    generator = GOSPAMetric(
        c=max_penalty,
        p=p,
        switching_penalty=switching_penalty
    )

    time = datetime.datetime.now()
    times = [time.now() + datetime.timedelta(seconds=i) for i in range(3)]
    tracks = {Track(states=[State(state_vector=[[i]], timestamp=time) for i, time
                            in zip([1, 2, 2], times)]),
              Track(states=[State(state_vector=[[i]], timestamp=time) for i, time
                            in zip([2, 1, 1], times)]),
              Track(states=[State(state_vector=[[i]], timestamp=time) for i, time
                            in zip([3, 100, 3], times)])}

    truths = {GroundTruthPath(states=[State(state_vector=[[i]], timestamp=time)
                                      for i, time in zip([1, 1, 1], times)]),
              GroundTruthPath(states=[State(state_vector=[[i]], timestamp=time)
                                      for i, time in zip([2, 2, 2], times)]),
              GroundTruthPath(states=[State(state_vector=[[i]], timestamp=time)
                                      for i, time in zip([3, 3, 3], times)])}

    manager = MultiManager([generator])
    manager.add_data({'groundtruth_paths': truths, 'tracks': tracks})
    main_metric = generator.compute_metric(manager)
    first_association, second_association, third_association = main_metric.value

    assert main_metric.time_range.start_timestamp == times[0]

    assert first_association.value['distance'] == 0
    assert first_association.value['localisation'] == 0
    assert first_association.value['missed'] == 0
    assert first_association.value['false'] == 0
    assert first_association.value['switching'] == 0
    assert first_association.timestamp == times[0]
    assert first_association.generator == generator

    assert abs(second_association.value['distance'] - np.power(
        max_penalty**p + (2.5**(1/p)*switching_penalty)**p, 1./p)) < 1e-9
    assert second_association.value['localisation'] == 0
    assert second_association.value['missed'] == 1*max_penalty
    assert second_association.value['false'] == 1*max_penalty
    assert abs(second_association.value['switching'] - 2.5**(1/p)*switching_penalty) < 1e-9
    assert second_association.timestamp == times[1]
    assert second_association.generator == generator

    assert abs(third_association.value['distance'] - 0.5**(1/p)*switching_penalty) < 1e-9
    assert third_association.value['localisation'] == 0
    assert third_association.value['missed'] == 0
    assert third_association.value['false'] == 0
    assert abs(third_association.value['switching'] - 0.5**(1/p)*switching_penalty) < 1e-9
    assert third_association.timestamp == times[2]
    assert third_association.generator == generator


def test_gospametric_single_timestep():
    """Test GOSPA on dataset with only a single time step."""
    max_penalty = 2
    switching_penalty = 3
    p = 2
    generator = GOSPAMetric(
        c=max_penalty,
        p=p,
        switching_penalty=switching_penalty
    )

    time = datetime.datetime.now()
    times = [time.now()]
    tracks = {Track(states=[State(state_vector=[[i]], timestamp=time) for i, time
                            in zip([1, 2, 2], times)]),
              Track(states=[State(state_vector=[[i]], timestamp=time) for i, time
                            in zip([2, 1, 1], times)]),
              Track(states=[State(state_vector=[[i]], timestamp=time) for i, time
                            in zip([3, 100, 3], times)])}

    truths = {GroundTruthPath(states=[State(state_vector=[[i]], timestamp=time)
                                      for i, time in zip([1, 1, 1], times)]),
              GroundTruthPath(states=[State(state_vector=[[i]], timestamp=time)
                                      for i, time in zip([2, 2, 2], times)]),
              GroundTruthPath(states=[State(state_vector=[[i]], timestamp=time)
                                      for i, time in zip([3, 3, 3], times)])}

    manager = MultiManager([generator])
    manager.add_data({'groundtruth_paths': truths, 'tracks': tracks})
    main_metric = generator.compute_metric(manager)

    assert main_metric.value['distance'] == 0
    assert main_metric.value['localisation'] == 0
    assert main_metric.value['missed'] == 0
    assert main_metric.value['false'] == 0
    assert main_metric.value['switching'] == 0
    assert main_metric.timestamp == times[0]
    assert main_metric.generator == generator


def test_gospametric_no_tracks():
    """Test GOSPA in the case of no tracks."""
    generator = GOSPAMetric(
        c=10,
        p=1
    )
    dummy_cost = (generator.c ** generator.p) / generator.alpha

    num_gt = 10
    num_timesteps = int(1e2)

    gt_distance = 30
    gt_speed = 10

    r = gt_distance*num_gt/(2*np.pi)
    w = gt_speed/(2*np.pi*r)

    ts = np.arange(num_timesteps, dtype=float)
    gt_offsets = 2*np.pi*np.linspace(0, 1, num_gt + 1)[:-1]
    gt_states = r*np.stack(
        (
            np.cos(w*ts[:, None] + gt_offsets[None, :]),
            np.sin(w*ts[:, None] + gt_offsets[None, :])
        )
    ).T

    time = datetime.datetime.now()
    tracks = {}
    truths = {
        GroundTruthPath(
            states=[
                State(
                    state_vector=gt_states[gt_idx, state_idx],
                    timestamp=time + datetime.timedelta(ts[state_idx])
                )
                for state_idx in range(gt_states.shape[1])
            ])
        for gt_idx in range(gt_states.shape[0])
    }

    manager = MultiManager([generator])
    manager.add_data({'groundtruth_paths': truths, 'tracks': tracks})
    main_metric = generator.compute_metric(manager)

    gospa_num_missed = np.fromiter((i.value['missed'] for i in main_metric.value), dtype=float)
    gospa_num_false = np.fromiter((i.value['false'] for i in main_metric.value), dtype=float)

    assert ((gospa_num_missed//dummy_cost) == num_gt).all()
    assert ((gospa_num_false//dummy_cost) == 0).all()


def test_gospametric_no_gts():
    """Test GOSPA of no ground truths."""
    generator = GOSPAMetric(
        c=10,
        p=1
    )
    dummy_cost = (generator.c ** generator.p) / generator.alpha

    rng = np.random.RandomState(42)

    num_gt = 10
    num_timesteps = int(1e2)

    gt_distance = 30
    gt_speed = 10
    track_position_sigma = 1

    r = gt_distance*num_gt/(2*np.pi)
    w = gt_speed/(2*np.pi*r)

    ts = np.arange(num_timesteps, dtype=float)
    gt_offsets = 2*np.pi*np.linspace(0, 1, num_gt + 1)[:-1]
    gt_states = r*np.stack(
        (
            np.cos(w*ts[:, None] + gt_offsets[None, :]),
            np.sin(w*ts[:, None] + gt_offsets[None, :])
        )
    ).T

    track_states = gt_states + rng.normal(0, track_position_sigma, gt_states.shape)

    time = datetime.datetime.now()
    tracks = {
        Track(states=[
            State(
                state_vector=track_states[track_idx, state_idx],
                timestamp=time + datetime.timedelta(ts[state_idx])
            )
            for state_idx in range(track_states.shape[1])
        ])
        for track_idx in range(track_states.shape[0])
    }
    truths = {}

    manager = MultiManager([generator])
    manager.add_data({'groundtruth_paths': truths, 'tracks': tracks})
    main_metric = generator.compute_metric(manager)

    gospa_num_missed = np.fromiter((i.value['missed'] for i in main_metric.value), dtype=float)
    gospa_num_false = np.fromiter((i.value['false'] for i in main_metric.value), dtype=float)

    assert ((gospa_num_missed//dummy_cost) == 0).all()
    assert ((gospa_num_false//dummy_cost) == num_gt).all()


def test_gospametric_occasional_no_tracks():
    """Test GOSPA for instances where some timesteps observe no tracks."""
    generator = GOSPAMetric(
        c=10,
        p=1
    )
    dummy_cost = (generator.c ** generator.p) / generator.alpha

    rng = np.random.RandomState(42)

    num_gt = 10
    num_timesteps = int(1e2)

    gt_distance = 30
    gt_speed = 10
    track_position_sigma = 1

    r = gt_distance*num_gt/(2*np.pi)
    w = gt_speed/(2*np.pi*r)

    ts = np.arange(num_timesteps, dtype=float)
    gt_offsets = 2*np.pi*np.linspace(0, 1, num_gt + 1)[:-1]
    gt_states = r*np.stack(
        (
            np.cos(w*ts[:, None] + gt_offsets[None, :]),
            np.sin(w*ts[:, None] + gt_offsets[None, :])
        )
    ).T

    track_states = gt_states + rng.normal(0, track_position_sigma, gt_states.shape)

    time = datetime.datetime.now()
    tracks = {
        Track(states=[
            State(
                state_vector=track_states[track_idx, state_idx],
                timestamp=time + datetime.timedelta(ts[state_idx])
            )
            for state_idx in range(track_states.shape[1]) if state_idx % 2 != 0
        ])
        for track_idx in range(track_states.shape[0])
    }
    truths = {
        GroundTruthPath(
            states=[
                State(
                    state_vector=gt_states[gt_idx, state_idx],
                    timestamp=time + datetime.timedelta(ts[state_idx])
                )
                for state_idx in range(gt_states.shape[1])
            ])
        for gt_idx in range(gt_states.shape[0])
    }

    manager = MultiManager([generator])
    manager.add_data({'groundtruth_paths': truths, 'tracks': tracks})
    main_metric = generator.compute_metric(manager)

    gospa_num_missed = np.fromiter((i.value['missed'] for i in main_metric.value), dtype=float)
    gospa_num_false = np.fromiter((i.value['false'] for i in main_metric.value), dtype=float)

    assert ((gospa_num_missed[::2]//dummy_cost) == num_gt).all()
    assert ((gospa_num_missed[1::2]//dummy_cost) == 0).all()
    assert ((gospa_num_false//dummy_cost) == 0).all()


def test_gospametric_occasional_no_gts():
    """Test GOSPA for instances where some timesteps observe no ground truths."""
    generator = GOSPAMetric(
        c=10,
        p=1
    )
    dummy_cost = (generator.c ** generator.p) / generator.alpha

    rng = np.random.RandomState(42)

    num_gt = 10
    num_timesteps = int(1e2)

    gt_distance = 30
    gt_speed = 10
    track_position_sigma = 1

    r = gt_distance*num_gt/(2*np.pi)
    w = gt_speed/(2*np.pi*r)

    ts = np.arange(num_timesteps, dtype=float)
    gt_offsets = 2*np.pi*np.linspace(0, 1, num_gt + 1)[:-1]
    gt_states = r*np.stack(
        (
            np.cos(w*ts[:, None] + gt_offsets[None, :]),
            np.sin(w*ts[:, None] + gt_offsets[None, :])
        )
    ).T

    track_states = gt_states + rng.normal(0, track_position_sigma, gt_states.shape)

    time = datetime.datetime.now()
    tracks = {
        Track(states=[
            State(
                state_vector=track_states[track_idx, state_idx],
                timestamp=time + datetime.timedelta(ts[state_idx])
            )
            for state_idx in range(track_states.shape[1])
        ])
        for track_idx in range(track_states.shape[0])
    }
    truths = {
        GroundTruthPath(
            states=[
                State(
                    state_vector=gt_states[gt_idx, state_idx],
                    timestamp=time + datetime.timedelta(ts[state_idx])
                )
                for state_idx in range(gt_states.shape[1]) if state_idx % 2 != 0
            ])
        for gt_idx in range(gt_states.shape[0])
    }

    manager = MultiManager([generator])
    manager.add_data({'groundtruth_paths': truths, 'tracks': tracks})
    main_metric = generator.compute_metric(manager)

    gospa_num_missed = np.fromiter((i.value['missed'] for i in main_metric.value), dtype=float)
    gospa_num_false = np.fromiter((i.value['false'] for i in main_metric.value), dtype=float)
    gospa_distance = np.fromiter((i.value['distance'] for i in main_metric.value), dtype=float)

    assert ((gospa_num_missed//dummy_cost) == 0).all()
    assert ((gospa_num_false[::2]//dummy_cost) == num_gt).all()
    assert ((gospa_distance[::2]//dummy_cost) == num_gt).all()


def test_gospametric_speed():
    """Test GOSPA compute speed."""
    generator = GOSPAMetric(
        c=10,
        p=1
    )
    dummy_cost = (generator.c ** generator.p) / generator.alpha

    rng = np.random.RandomState(42)

    num_gt = 10
    num_missed = 3
    num_false_positives = 2
    num_true_positives = num_gt - num_missed
    num_timesteps = int(1e3)

    gt_distance = 30
    gt_speed = 10
    track_position_sigma = 1

    r = gt_distance*num_gt/(2*np.pi)
    w = gt_speed/(2*np.pi*r)

    ts = np.arange(num_timesteps, dtype=float)
    gt_offsets = 2*np.pi*np.linspace(0, 1, num_gt + 1)[:-1]
    gt_states = r*np.stack(
        (
            np.cos(w*ts[:, None] + gt_offsets[None, :]),
            np.sin(w*ts[:, None] + gt_offsets[None, :])
        )
    ).T

    track_states = np.vstack(
        (
            gt_states[:num_true_positives],
            5*gt_states[:num_false_positives]
        )
    )
    track_states += rng.normal(0, track_position_sigma, track_states.shape)

    time = datetime.datetime.now()
    tracks = {
        Track(states=[
            State(
                state_vector=track_states[track_idx, state_idx],
                timestamp=time + datetime.timedelta(ts[state_idx])
            )
            for state_idx in range(track_states.shape[1])
        ])
        for track_idx in range(track_states.shape[0])
    }
    truths = {
        GroundTruthPath(
            states=[
                State(
                    state_vector=gt_states[gt_idx, state_idx],
                    timestamp=time + datetime.timedelta(ts[state_idx])
                )
                for state_idx in range(gt_states.shape[1])
            ])
        for gt_idx in range(gt_states.shape[0])
    }

    manager = MultiManager([generator])
    manager.add_data({'groundtruth_paths': truths, 'tracks': tracks})
    main_metric = generator.compute_metric(manager)

    gospa_num_missed = np.fromiter((i.value['missed'] for i in main_metric.value), dtype=float)
    gospa_num_false = np.fromiter((i.value['false'] for i in main_metric.value), dtype=float)

    assert main_metric.title == "GOSPA Metrics"
    assert ((gospa_num_missed//dummy_cost) == num_missed).all()
    assert ((gospa_num_false//dummy_cost) == num_false_positives).all()


@pytest.mark.parametrize(
    'p,first_value,second_value',
    ((1, 2.4, 2.16), (2, 4.49444, 4.47571), (np.inf, 10, 10)),
    ids=('p=1', 'p=2', 'p=inf'))
def test_ospa_computemetric_cardinality_error(p, first_value, second_value):
    generator = OSPAMetric(
        c=10,
        p=p
    )

    time = datetime.datetime.now()
    # Multiple tracks and truths present at two timesteps
    tracks = {Track(states=[State(state_vector=[[i + 0.5]], timestamp=time),
                            State(state_vector=[[i + 1.2]],
                                  timestamp=time + datetime.timedelta(seconds=1))])
              for i in range(4)}
    truths = {GroundTruthPath(
        states=[GroundTruthState(state_vector=[[i]], timestamp=time),
                GroundTruthState(state_vector=[[i + 1]],
                                 timestamp=time+datetime.timedelta(seconds=1))])
              for i in range(5)}

    manager = MultiManager([generator])
    manager.add_data({'groundtruth_paths': truths, 'tracks': tracks})
    main_metric = generator.compute_metric(manager)
    first_association, second_association = main_metric.value

    assert main_metric.title == "OSPA distances"
    assert main_metric.time_range.start_timestamp == time
    assert main_metric.time_range.end_timestamp == time + datetime.timedelta(
        seconds=1)

    assert first_association.title == "OSPA distance"
    assert first_association.value == pytest.approx(first_value)
    assert first_association.timestamp == time
    assert first_association.generator == generator

    assert second_association.title == "OSPA distance"
    assert second_association.value == pytest.approx(second_value)
    assert second_association.timestamp == time + datetime.timedelta(seconds=1)
    assert second_association.generator == generator


@pytest.mark.parametrize("associations, expected_losses", [
    ([
        {0: 0, 1: 1, 2: 2},
        {0: 0, 1: 1, 2: 2},
        {0: 0, 1: 1, 2: None},
        {0: 0, 1: 1, 2: 2},
        {0: 1, 1: 0, 2: 2},
        {1: 0, 0: 1, 2: 2},
        {0: None, 1: 2, 2: 0},
    ],  [0, 0, 0.5, 0.5, 2, 0, 2.5]),
    ([
        {0: 0, 1: 1, 2: 2},
        {0: None, 1: None, 2: None},
        {0: 3, 1: None, 2: None},
    ], [0, 1.5, 0.5]),
    ([
        {0: None, 1: None, 2: None},
        {0: 0, 1: 1, 2: 2},
    ], [0, 0]),
    ([  # The first time we associate with the track it should not count for loss
        {0: None, 1: None, 2: None},
        {0: 0, 1: 1, 2: 2},
    ], [0, 0]),
    ([  # The first time we associate with the track it should not count for loss
        {0: 0},
        {0: 0, 1: 1},
        {0: 0, 1: 1, 2: 3}
    ], [0, 0, 0]),
    ([  # We don't want loss if we just didn't see it
        {0: 0, 1: 1},
        {0: 0},
        {0: 0, 1: 1},
        {0: 0, 1: 2}
    ], [0, 0, 0, 1]),
 ])
def test_switching_loss(associations, expected_losses):
    loss_factor = 1

    switching_loss = _SwitchingLoss(loss_factor, 1)

    with pytest.raises(RuntimeError) as _:
        switching_loss.loss()   # Should raise error if no associations have been added yet.

    for association, expected_loss in zip(associations, expected_losses):
        switching_loss.add_associations(association)
        assert switching_loss.loss() == expected_loss
