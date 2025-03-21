from collections.abc import Sequence

from .array import StateVectors
from .base import Type
from .hypothesis import Hypothesis, CompositeHypothesis
from .mixture import GaussianMixture
from .state import CreatableFromState, CompositeState, KernelParticleState
from .state import State, GaussianState, ParticleState, EnsembleState, \
    SqrtGaussianState, InformationState, CategoricalState, ASDGaussianState, \
    WeightedGaussianState, TaggedWeightedGaussianState, ASDTaggedWeightedGaussianState, \
    MultiModelParticleState, RaoBlackwellisedParticleState, BernoulliParticleState
from ..base import Property


class Update(Type, CreatableFromState):
    """ Update type

    The base update class. Updates are returned by :class:'~.Updater' objects
    and contain the information that was used to perform the updating"""

    hypothesis: Hypothesis = Property(doc="Hypothesis used for updating")


class StateUpdate(Update, State):
    """ StateUpdate type

    Most simple state update type, where everything only has time
    and a state vector. Requires a prior state that was updated,
    and the hypothesis used to update the prior.
    """


class GaussianStateUpdate(Update, GaussianState):
    """ GaussianStateUpdate type

    This is a simple Gaussian state update object, which, as the name
    suggests, is described by a Gaussian distribution.
    """


class SqrtGaussianStateUpdate(Update, SqrtGaussianState):
    """ SqrtGaussianStateUpdate type

    This is equivalent to a Gaussian state update object, but with the
    covariance of the Gaussian distribution stored in matrix square root
    form.
    """


class WeightedGaussianStateUpdate(Update, WeightedGaussianState):
    """ WeightedGaussianStateUpdate type

    This is a simple Gaussian state update object, which, as the name suggests, is described
    by a Gaussian distribution with an associated weight.
    """


class TaggedWeightedGaussianStateUpdate(Update, TaggedWeightedGaussianState):
    """ TaggedWeightedGaussianStateUpdate type

    This is a simple Gaussian state update object, which, as the name suggests, is described
    by a Gaussian distribution, with an associated weight and unique tag.
    """


class GaussianMixtureUpdate(Update, GaussianMixture):
    """ GaussianMixtureUpdate type

    This is a Gaussian mixture update object, which, as the name
    suggests, is described by a Gaussian mixture.
    """


class ASDGaussianStateUpdate(Update, ASDGaussianState):
    """ ASDGaussianStateUpdate type

    This is a simple ASD Gaussian state update object, which, as the name
    suggests, is described by a Gaussian distribution.
    """


class ASDTaggedWeightedGaussianStateUpdate(Update, ASDTaggedWeightedGaussianState):
    """ASDTaggedWeightedGaussianStateUpdate type"""


class ParticleStateUpdate(Update, ParticleState):
    """ParticleStateUpdate type

    This is a simple Particle state update object.
    """


class MultiModelParticleStateUpdate(Update, MultiModelParticleState):
    """MultiModelStateUpdate type

    This is a simple Multi-Model Particle state update object.
    """


class RaoBlackwellisedParticleStateUpdate(Update, RaoBlackwellisedParticleState):
    """RaoBlackwellisedStateUpdate type

    This is a simple Rao Blackwellised Particle state update object.
    """


class BernoulliParticleStateUpdate(Update, BernoulliParticleState):
    """BernoulliStateUpdate type

    This is a simple Bernoulli Particle state update object.
    """


class KernelParticleStateUpdate(Update, KernelParticleState):
    """KernelParticleStateUpdate type

    This is a Kernel Particle state update object.
    """
    proposal: StateVectors = Property(default=None,
                                      doc='Kernel covariance value. Default `None`.')


class EnsembleStateUpdate(Update, EnsembleState):
    """EnsembleStateUpdate type

    This is a simple Ensemble state update object.
    """


class InformationStateUpdate(Update, InformationState):
    """ InformationUpdate type

    This is a simple Information state update object, which, as the name
    suggests, is described by a precision matrix and its corresponding state vector.
    """


class CategoricalStateUpdate(Update, CategoricalState):
    """Categorical state prediction type"""


class CompositeUpdate(Update, CompositeState):
    """Composite update type

    Composition of :class:`~.Update`.
    """

    sub_states: Sequence[Update] = Property(
        doc="Sequence of sub-updates comprising the composite update. All sub-updates must have "
            "matching timestamp. Must not be empty.")
    hypothesis: CompositeHypothesis = Property(doc="Hypothesis used for updating")
