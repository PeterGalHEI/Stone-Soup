import warnings

from .base import Hypothesiser
from ..base import Property
from ..types.multihypothesis import MultipleHypothesis
from ..types.numeric import Probability
from ..types.prediction import Prediction


class MFAHypothesiser(Hypothesiser):
    """Multi-Frame Assignment Hypothesiser based on an underlying Hypothesiser

    Generates a list of SingleHypotheses pertaining to individual component-detection hypotheses

    Note
    ----
    This is to be used in conjunction with the :class:`~.MFADataAssociator`

    References
    ----------
    1. Xia, Y., Granström, K., Svensson, L., García-Fernández, Á.F., and Williams, J.L.,
       2019. Multiscan Implementation of the Trajectory Poisson Multi-Bernoulli Mixture Filter.
       J. Adv. Information Fusion, 14(2), pp. 213–235.
    """

    hypothesiser: Hypothesiser = Property(
        doc="Underlying hypothesiser used to generate detection-target pairs")

    def hypothesise(self, track, detections, timestamp, detections_tuple, **kwargs):
        """Form hypotheses for associations between Detections and a given track.

        Parameters
        ----------
        track: :class:`~.Track`
            The track object to hypothesise on
        detections : set of :class:`~.Detection`
            Retrieved measurements
        timestamp : datetime
            Time of the detections/predicted states
        detections_tuple : tuple of :class:`~.Detection`
            Original tuple of detections required for consistent indexing
        Returns
        -------
        : :class:`~.MultipleHypothesis`
            A container of :class:`~.SingleProbabilityHypothesis` objects, pertaining to individual
            component-detection hypotheses
        """

        # Check to make sure all detections are obtained from the same time
        timestamps = {detection.timestamp for detection in detections}
        if len(timestamps) > 1:
            warnings.warn("All detections should have the same timestamp")

        hypotheses = list()
        component_weight_sum = Probability.sum(
                component.weight for component in track.state.components)
        for component in track.state.components:
            # Get hypotheses for that component for all measurements
            component_hypotheses = self.hypothesiser.hypothesise(
                component, detections, timestamp, **kwargs)
            for hypothesis in component_hypotheses:
                # Update component tag and weight
                det_idx = detections_tuple.index(hypothesis.measurement) + 1 if hypothesis else 0
                new_weight = Probability(component.weight * hypothesis.weight)
                new_weight /= component_weight_sum
                hypothesis.prediction = \
                    Prediction.from_state(
                        hypothesis.prediction,
                        tag=[*component.tag, det_idx],  # TODO: Avoid dependency on indexes
                        weight=new_weight,
                    )
                hypotheses.append(hypothesis)
        # Create Multiple Hypothesis and add to list
        hypotheses = MultipleHypothesis(hypotheses)

        return hypotheses
