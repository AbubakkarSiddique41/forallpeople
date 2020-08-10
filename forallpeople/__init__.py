#    Copyright 2020 Connor Ferster

#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""
The SI Units: "For all people, for all time"

A module to model the seven SI base units:

                    kg

            cd               m


                    SI
         mol                    s



               K           A

  ...and other derived and non-SI units for practical calculations.
"""

__version__ = "2.0.0"

from typing import Union, Optional


from forallpeople.dimensions import Dimensions
import forallpeople.physical_helper_functions as phf
import forallpeople.tuplevector as vec
from forallpeople.si_environment import Environment
import builtins
import sys

NUMBER = (int, float)

class Physical(object):
    """
    A class that defines any physical quantity that can be described
    within the BIPM SI unit system.
    """

    _eps = 1e-7
    _total_precision = 6

    __slots__ = ("value", "dimensions", "factor", "precision", "_prefixed")

    def __init__(
        self,
        value: Union[int, float],
        dimensions: Dimensions,
        factor: float,
        precision: int = 3,
        prefixed: str = "",
    ):
        """Constructor"""
        super(Physical, self).__setattr__("value", value)
        super(Physical, self).__setattr__("dimensions", dimensions)
        super(Physical, self).__setattr__("factor", factor)
        super(Physical, self).__setattr__("precision", precision)
        super(Physical, self).__setattr__("_prefixed", prefixed)

    def __setattr__(self, _, __):
        raise AttributeError("Cannot set attribute.")

    ### API Methods ###
    @property
    def latex(self) -> str:
        return self._repr_latex_()

    @property
    def html(self) -> str:
        return self._repr_html_()

    def prefixed(self, prefixed: str = ""):
        """
        Return a Physical instance with 'prefixed' property set to 'prefix'
        """
        if self.factor != 1:
            raise AttributeError("Cannot prefix a Physical if it has a factor.")
        # check if elligible for prefixing; do not rely on __repr__ to ignore it
        return Physical(
            self.value, self.dimensions, self.factor, self.precision, prefixed
        )

    @property
    def repr(self) -> str:
        """
        Returns a repr that can be used to create another Physical instance.
        """
        repr_str = (
            "Physical(value={}, dimensions={}, factor={}, precision={}, _prefixed={})"
        )
        return repr_str.format(
            self.value, self.dimensions, self.factor, self.precision, self._prefixed
        )  # check

    def round(self, n: int):
        """
        Returns a new Physical with a new precision, 'n'. Precision controls
        the number of decimal places displayed in repr and str.
        """
        return Physical(self.value, self.dimensions, self.factor, n, self._prefixed)

    def split(self, base_value: bool = True) -> tuple:
        """
        Returns a tuple separating the value of `self` with the units of `self`.
        If base_value is True, then the value will be the value in base units. If False, then
        the apparent value of `self` will be used.

        This method is to allow flexibility in working with Physical instances when working
        with numerically optimized libraries such as numpy which cannot accept non-numerical
        objects in some of their operations (such as in matrix inversion).
        """
        if base_value:
            return (
                self.value * self.factor,
                Physical(1 / self.factor, self.dimensions, self.factor, self.precision),
            )
        return (float(self), Physical(1, self.dimensions, self.factor, self.precision))

    def sqrt(self, n: float = 2.0):
        """
        Returns a Physical instance that represents the square root of `self`.
        `n` can be set to an alternate number to compute an alternate root (e.g. 3.0 for cube root)
        """
        return self ** (1 / n)

    def to(self, unit_name=""):
        """
        Returns None and alters the instance into one of the elligible
        alternative units for its dimension, if it exists in the alternative_units dict;
        """
        dims = self.dimensions
        env_dims = environment.units_by_dimension
        derived = env_dims["derived"]
        defined = env_dims["defined"]
        power, dims_orig = phf._powers_of_derived(dims, env_dims)
        if not unit_name:
            print("Available units: ")
            for key in derived.get(dims_orig, {}):
                print(key)
            for key in defined.get(dims_orig, {}):
                print(key)

        if unit_name:
            defined_match = defined.get(dims_orig, {}).get(unit_name, {})
            derived_match = derived.get(dims_orig, {}).get(unit_name, {})
            unit_match = defined_match or derived_match
            new_factor = unit_match.get("Factor", 1) ** power
            return Physical(self.value, self.dimensions, new_factor, self.precision)

    def si(self):
        """
        Return a new Physical instance with self.factor set to 1, thereby returning
        the instance to SI units display.
        """
        return Physical(self.value, self.dimensions, 1, self.precision)

    ### repr Methods (the "workhorse" of Physical) ###

    def __repr__(self):
        return self._repr_template_()

    def _repr_html_(self):
        return self._repr_template_(template="html")

    def _repr_markdown_(self):
        return self._repr_template_(template="html")

    def _repr_latex_(self):
        return self._repr_template_(template="latex")

    def _repr_template_(self, template: str = "") -> str:
        """
        Returns a string that appropriately represents the Physical
        instance. The parameter,'template', allows two optional values:
        'html' and 'latex'. which will only be utilized if the Physical
        exists in the Jupyter/iPython environment.
        """
        # Access req'd attributes
        precision = self.precision
        dims = self.dimensions
        factor = self.factor
        val = self.value
        prefix = ""
        prefixed = self._prefixed
        eps = self._eps

        # Access external environment
        env_fact = environment.units_by_factor or dict()
        env_dims = environment.units_by_dimension or dict()

        # Do the expensive vector math method (call once, only)
        power, dims_orig = phf._powers_of_derived(dims, env_dims)

        # Determine if there is a symbol for these dimensions in the environment
        # and if the quantity is elligible to be prefixed
        symbol, prefix_bool = phf._evaluate_dims_and_factor(
            dims_orig, factor, power, env_fact, env_dims
        )
        # Get the appropriate prefix
        if prefix_bool and prefixed:
            prefix = prefixed
        elif prefix_bool and dims_orig == Dimensions(1, 0, 0, 0, 0, 0, 0):
            prefix = phf._auto_prefix(val, power, kg=True)
        elif prefix_bool:
            prefix = phf._auto_prefix(val, power, kg=False)

        # Format the exponent (may not be used, though)
        exponent = phf._format_exponent(power, repr_format=template, eps=eps)

        # Format the units
        if not symbol and phf._dims_basis_multiple(dims):
            components = phf._get_unit_components_from_dims(dims)
            units_symbol = phf._get_unit_string(components, repr_format=template)
            units = units_symbol
            units = phf._format_symbol(prefix, units_symbol, repr_format=template)
            exponent = ""
        elif not symbol:
            components = phf._get_unit_components_from_dims(dims)
            units_symbol = phf._get_unit_string(components, repr_format=template)
            units = units_symbol
            exponent = ""
        else:
            units = phf._format_symbol(prefix, symbol, repr_format=template)

        # Determine the appropriate display value
        value = val * factor

        if prefix_bool:
            # If the quantity has a "pre-fixed" prefix, it will override
            # the value generated in _auto_prefix_value
            if dims_orig == Dimensions(1, 0, 0, 0, 0, 0, 0):
                value = phf._auto_prefix_value(val, power, prefixed, kg=True)
            else:
                value = phf._auto_prefix_value(val, power, prefixed)

        pre_super = ""
        post_super = ""
        space = " "
        if template == "latex":
            space = r"\ "
            pre_super = "^{"
            post_super = "}"
        elif template == "html":
            space = " "
            pre_super = "<sup>"
            post_super = "</sup>"

        if not exponent:
            pre_super = ""
            post_super = ""

        return f"{value:.{precision}f}{space}{units}{pre_super}{exponent}{post_super}"

    ### "Magic" Methods ###

    def __float__(self):
        value = self.value
        dims = self.dimensions
        factor = self.factor
        prefixed = self._prefixed
        env_dims = environment.units_by_dimension or dict()
        power, _ = phf._powers_of_derived(dims, env_dims)
        if factor != 1:
            float_value = value * factor
        else:
            float_value = phf._auto_prefix_value(value, power, prefixed)
        return float(float_value)

    def __int__(self):
        return int(float(self))

    def __neg__(self):
        return self * -1

    def __abs__(self):
        if self.value < 0:
            return self * -1
        return self

    def __bool__(self):
        return True

    # def __format__(self, fmt_spec = ''):
    #     components = (format(c, fmt_spec) for c in self)
    #     return '({}, {})'.format(*components)

    def __hash__(self):
        return hash(
            (self.value, self.dimensions, self.factor, self.precision, self._prefixed)
        )

    def __round__(self, n=0):
        return self.round(n)

    def __contains__(self, other):
        return False

    def __eq__(self, other):
        if isinstance(other, NUMBER):
            return round(self.value, phf._total_precision) == other
        elif type(other) == str:
            return False
        elif isinstance(other, Physical) and self.dimensions == other.dimensions:
            return round(self.value, phf._total_precision) == round(
                other.value, phf._total_precision
            )
        else:
            raise ValueError(
                "Can only compare between Physical instances of equal dimension."
            )

    def __gt__(self, other):
        if isinstance(other, NUMBER):
            return round(self.value, phf._total_precision) > other
        elif isinstance(other, Physical) and self.dimensions == other.dimensions:
            return round(self.value, phf._total_precision) > round(
                other.value, phf._total_precision
            )
        else:
            raise ValueError(
                "Can only compare between Physical instances of equal dimension."
            )

    def __ge__(self, other):
        if isinstance(other, NUMBER):
            return round(self.value, phf._total_precision) >= other
        elif isinstance(other, Physical) and self.dimensions == other.dimensions:
            return round(self.value, phf._total_precision) >= round(
                other.value, phf._total_precision
            )
        else:
            raise ValueError(
                "Can only compare between Physical instances of equal dimension."
            )

    def __lt__(self, other):
        if isinstance(other, NUMBER):
            return round(self.value, phf._total_precision) < other
        elif isinstance(other, Physical) and self.dimensions == other.dimensions:
            return round(self.value, phf._total_precision) < round(
                other.value, phf._total_precision
            )
        else:
            raise ValueError(
                "Can only compare between Physical instances of equal dimension."
            )

    def __le__(self, other):
        if isinstance(other, NUMBER):
            return round(self.value, phf._total_precision) <= other
        elif isinstance(other, Physical) and self.dimensions == other.dimensions:
            return round(self.value, phf._total_precision) <= round(
                other.value, phf._total_precision
            )
        else:
            raise ValueError(
                "Can only compare between Physical instances of equal dimension."
            )

    def __add__(self, other):
        if isinstance(other, Physical):
            if self.dimensions == other.dimensions:
                try:
                    return Physical(
                        self.value + other.value,
                        self.dimensions,
                        self.factor,
                        self.precision,
                        self._prefixed,
                    )
                except:
                    raise ValueError(
                        f"Cannot add between {self} and {other}: "
                        + ".value attributes are incompatible."
                    )
            else:
                raise ValueError(
                    f"Cannot add between {self} and {other}: "
                    + ".dimensions attributes are incompatible (not equal)"
                )
        else:
            try:
                other = other / self.factor
                return Physical(
                    self.value + other,
                    self.dimensions,
                    self.factor,
                    self.precision,
                    self._prefixed,
                )
            except:
                raise ValueError(
                    f"Cannot add between {self} and {other}: "
                    + ".value attributes are incompatible."
                )

    def __radd__(self, other):
        return self.__add__(other)

    def __iadd__(self, other):
        raise ValueError(
            "Cannot incrementally add Physical instances because they are immutable."
            + " Use 'a = a + b', to make the operation explicit."
        )

    def __sub__(self, other):
        if isinstance(other, Physical):
            if self.dimensions == other.dimensions:
                try:
                    return Physical(
                        self.value - other.value,
                        self.dimensions,
                        self.factor,
                        self.precision,
                        self._prefixed,
                    )
                except:
                    raise ValueError(f"Cannot subtract between {self} and {other}")
            else:
                raise ValueError(
                    f"Cannot subtract between {self} and {other}:"
                    + ".dimensions attributes are incompatible (not equal)"
                )
        else:
            try:
                other = other / self.factor
                return Physical(
                    self.value - other,
                    self.dimensions,
                    self.factor,
                    self.precision,
                    self._prefixed,
                )
            except:
                raise ValueError(
                    f"Cannot subtract between {self} and {other}: "
                    + ".value attributes are incompatible."
                )

    def __rsub__(self, other):
        if isinstance(other, Physical):
            return self.__sub__(other)
        else:
            try:
                other = other / self.factor
                return Physical(
                    other - self.value,
                    self.dimensions,
                    self.factor,
                    self.precision,
                    self._prefixed,
                )
            except:
                raise ValueError(
                    f"Cannot subtract between {self} and {other}: "
                    + ".value attributes are incompatible."
                )

    def __isub__(self, other):
        raise ValueError(
            "Cannot incrementally subtract Physical instances because they are immutable."
            + " Use 'a = a - b', to make the operation explicit."
        )

    def __mul__(self, other):
        if isinstance(other, NUMBER):
            return Physical(
                self.value * other,
                self.dimensions,
                self.factor,
                self.precision,
                self._prefixed,
            )

        elif isinstance(other, Physical):
            new_dims = vec.add(self.dimensions, other.dimensions)
            new_power, new_dims_orig = phf._powers_of_derived(
                new_dims, environment.units_by_dimension
            )
            new_factor = self.factor * other.factor
            test_factor = phf._get_units_by_factor(
                new_factor, new_dims_orig, environment.units_by_factor, new_power
            )
            if not test_factor:
                new_factor = 1
            try:
                new_value = self.value * other.value
            except:
                raise ValueError(
                    f"Cannot multiply between {self} and {other}: "
                    + ".value attributes are incompatible."
                )
            if new_dims == Dimensions(0, 0, 0, 0, 0, 0, 0):
                return new_value
            else:
                return Physical(new_value, new_dims, new_factor, self.precision)
        else:
            try:
                return Physical(
                    self.value * other, self.dimensions, self.factor, self.precision
                )
            except:
                raise ValueError(
                    f"Cannot multiply between {self} and {other}: "
                    + ".value attributes are incompatible."
                )

    def __imul__(self, other):
        raise ValueError(
            "Cannot incrementally multiply Physical instances because they are immutable."
            + " Use 'a = a * b' to make the operation explicit."
        )

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        if isinstance(other, NUMBER):
            return Physical(
                self.value / other,
                self.dimensions,
                self.factor,
                self.precision,
                self._prefixed,
            )
        elif isinstance(other, Physical):
            new_dims = vec.subtract(self.dimensions, other.dimensions)
            new_power, new_dims_orig = phf._powers_of_derived(
                new_dims, environment.units_by_dimension
            )
            new_factor = self.factor / other.factor
            if not phf._get_units_by_factor(
                new_factor, new_dims_orig, environment.units_by_factor, new_power
            ):
                new_factor = 1
            try:
                new_value = self.value / other.value
            except:
                raise ValueError(
                    f"Cannot divide between {self} and {other}: "
                    + ".value attributes are incompatible."
                )
            if new_dims == Dimensions(0, 0, 0, 0, 0, 0, 0):
                return new_value
            else:
                return Physical(new_value, new_dims, new_factor, self.precision)
        else:
            try:
                return Physical(
                    self.value / other, self.dimensions, self.factor, self.precision
                )
            except:
                raise ValueError(
                    f"Cannot divide between {self} and {other}: "
                    + ".value attributes are incompatible."
                )

    def __rtruediv__(self, other):
        if isinstance(other, NUMBER):
            new_value = other / self.value
            new_dimensions = vec.multiply(self.dimensions, -1)
            new_factor = self.factor ** -1  # added new_factor
            return Physical(
                new_value,
                new_dimensions,
                new_factor,  # updated from self.factor to new_factor
                self.precision,
            )
        else:
            try:
                return Physical(
                    other / self.value,
                    vec.multiply(self.dimensions, -1),
                    self.factor ** -1,  # updated to ** -1
                    self.precision,
                )
            except:
                raise ValueError(
                    f"Cannot divide between {other} and {self}: "
                    + ".value attributes are incompatible."
                )

    def __itruediv__(self, other):
        raise ValueError(
            "Cannot incrementally divide Physical instances because they are immutable."
            + " Use 'a = a / b' to make the operation explicit."
        )

    def __pow__(self, other):
        if isinstance(other, NUMBER):
            if self._prefixed:
                return float(self) ** other
            new_value = self.value ** other
            new_dimensions = vec.multiply(self.dimensions, other)
            new_factor = self.factor ** other
            return Physical(new_value, new_dimensions, new_factor, self.precision)
        else:
            raise ValueError(
                "Cannot raise a Physical to the power of \
                                     another Physical -> ({self}**{other})".format(
                    self, other
                )
            )


# The seven SI base units...
_the_si_base_units = {
    "kg": Physical(1, Dimensions(1, 0, 0, 0, 0, 0, 0), 1.0),
    "m": Physical(1, Dimensions(0, 1, 0, 0, 0, 0, 0), 1.0),
    "s": Physical(1, Dimensions(0, 0, 1, 0, 0, 0, 0), 1.0),
    "A": Physical(1, Dimensions(0, 0, 0, 1, 0, 0, 0), 1.0),
    "cd": Physical(1, Dimensions(0, 0, 0, 0, 1, 0, 0), 1.0),
    "K": Physical(1, Dimensions(0, 0, 0, 0, 0, 1, 0), 1.0),
    "mol": Physical(1, Dimensions(0, 0, 0, 0, 0, 0, 1), 1.0),
}

environment = Environment(Physical, builtins, _the_si_base_units)
environment.push_vars(_the_si_base_units, sys.modules[__name__])

