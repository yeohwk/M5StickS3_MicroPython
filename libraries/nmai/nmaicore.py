"""
Pure-MicroPython implementation of the NeuroMem/NMAI core used by nmaicore.cpp.

Designed for M5StickS3 / UIFlow 2.0.  It implements the public learning,
classification, context, neuron import/export and register-style APIs without
requiring a native C++ extension.

The implementation allocates only committed neurons, which is substantially
more memory-efficient in MicroPython than pre-allocating 1024 Python objects.
"""

try:
    from math import sqrt
except ImportError:
    sqrt = None

# Register addresses
NM_NCR = 0x00
NM_COMP = 0x01
NM_LCOMP = 0x02
NM_DIST = 0x03
NM_INDEXCOMP = 0x03
NM_CAT = 0x04
NM_AIF = 0x05
NM_MINIF = 0x06
NM_MAXIF = 0x07
NM_TESTCOMP = 0x08
NM_TESTCAT = 0x09
NM_NID = 0x0A
NM_GCR = 0x0B
NM_RESETCHAIN = 0x0C
NM_NSR = 0x0D
NM_NCOUNT = 0x0F
NM_FORGET = 0x0F

# Status / mode bits
SR = 0x0010
KNN = 0x0020
IDN = 0x0008
UNC = 0x0004
NORM = 0x0080

NORM_L1 = 0
NORM_LSUP = 1
NORM_Lsup = NORM_LSUP       # compatibility with the C++ spelling
CLASSIFIER_RBF = 0
CLASSIFIER_KNN = 1

DEFMAXIF = 0x4000
DEFMINIF = 0x0002
DEFGCR = 0x01

CLREXR = 0x0000
EXT_L2 = 0x0001

VECTORSIZE = 256
NETWORKSIZE = 1024
NM_VERSION = 0x0001
UNIQUE_ID = 0x1785

# Compact neuron record indexes
_N_CONTEXT = 0
_N_VECTOR = 1
_N_AIF = 2
_N_MINIF = 3
_N_CATEGORY = 4
_N_IDENTIFIER = 5


class NMAICore:
    """Software model of the NMAI/NeuroMem learning core."""

    def __init__(self, network_size=NETWORKSIZE, vector_size=VECTORSIZE):
        self.network_size = int(network_size)
        self.vector_size = int(vector_size)
        if self.network_size <= 0:
            raise ValueError("network_size must be positive")
        if self.vector_size <= 0 or self.vector_size > VECTORSIZE:
            raise ValueError("vector_size must be between 1 and 256")

        self._neurons = []
        self._context = DEFGCR
        self._minif = DEFMINIF
        self._maxif = DEFMAXIF
        self._nsr = 0
        self._exr = 0

        self._comp_index = 0
        self._chain_index = 0
        self._input_buffer = bytearray(self.vector_size)
        self._last_length = 0
        self._results = []
        self._result_index = 0
        self._top_identifier = 0xFFFFFFFF

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------
    @staticmethod
    def _u16(value):
        return int(value) & 0xFFFF

    @staticmethod
    def _byte(value):
        return int(value) & 0xFF

    def _normalise_vector(self, vector, length=None):
        if vector is None:
            raise ValueError("vector cannot be None")
        if length is None:
            length = len(vector)
        length = int(length)
        if length <= 0 or length > self.vector_size:
            raise ValueError("length must be between 1 and vector_size")
        if len(vector) < length:
            raise ValueError("vector is shorter than length")

        out = bytearray(length)
        for i in range(length):
            value = int(vector[i])
            if value < 0 or value > 255:
                raise ValueError("vector components must be in range 0..255")
            out[i] = value
        return out

    def _context_matches(self, neuron):
        active = self._context & 0x7F
        return active == 0 or neuron[_N_CONTEXT] == active

    def _distance(self, vector, neuron):
        model = neuron[_N_VECTOR]
        length = len(vector)

        if self._exr & EXT_L2:
            total = 0
            for i in range(length):
                d = int(vector[i]) - int(model[i])
                total += d * d
            # MicroPython provides math.sqrt on UIFlow firmware.
            return int(sqrt(total)) if sqrt is not None else int(total ** 0.5)

        if self._context & NORM:
            largest = 0
            for i in range(length):
                d = abs(int(vector[i]) - int(model[i]))
                if d > largest:
                    largest = d
            return largest

        total = 0
        for i in range(length):
            total += abs(int(vector[i]) - int(model[i]))
        return total

    def _evaluate(self, vector):
        results = []
        knn_mode = bool(self._nsr & KNN)

        for neuron in self._neurons:
            if not self._context_matches(neuron):
                continue
            distance = self._distance(vector, neuron)
            if knn_mode or distance < neuron[_N_AIF]:
                results.append((
                    distance,
                    neuron[_N_CATEGORY],
                    neuron[_N_IDENTIFIER],
                    neuron,
                ))

        # Deterministic ordering: nearest first, then base category, then ID.
        results.sort(key=lambda item: (
            item[0], item[1] & 0x7FFF, item[2]
        ))

        self._results = results
        self._result_index = 0
        self._top_identifier = results[0][2] if results else 0xFFFFFFFF

        self._nsr &= ~(IDN | UNC)
        if results:
            first_category = results[0][1] & 0x7FFF
            uncertain = False
            for item in results[1:]:
                if (item[1] & 0x7FFF) != first_category:
                    uncertain = True
                    break
            if uncertain:
                self._nsr |= UNC
            else:
                self._nsr |= IDN
        return self._nsr

    def _new_neuron(self, vector, category, aif):
        model = bytearray(self.vector_size)
        model[:len(vector)] = vector
        identifier = len(self._neurons) + 1
        return [
            self._context & 0x7F,
            model,
            int(aif),
            int(self._minif),
            int(category) & 0xFFFF,
            identifier,
        ]

    # ---------------------------------------------------------
    # Public high-level API
    # ---------------------------------------------------------
    def forget(self):
        """Clear all committed neurons and reset the recognition state."""
        self._neurons = []
        self._comp_index = 0
        self._chain_index = 0
        self._results = []
        self._result_index = 0
        self._last_length = 0
        self._nsr &= KNN

    def reset_chain(self):
        self._chain_index = 0
        self._comp_index = 0
        self._result_index = 0

    def size_network(self, size):
        size = int(size)
        if size <= 0:
            raise ValueError("size must be positive")
        self.network_size = size
        self.forget()

    def get_unique_id(self):
        return UNIQUE_ID

    def get_version(self):
        return NM_VERSION

    def set_extended_function(self, func_type):
        self._exr |= self._u16(func_type)

    def clear_extended_function(self, func_type):
        self._exr &= ~self._u16(func_type)

    def get_extended_function(self):
        return self._exr & 0xFFFF

    def enable_l2_norm(self):
        self._exr |= EXT_L2

    def disable_l2_norm(self):
        self._exr &= ~EXT_L2

    def set_rbf_classifier(self):
        self._nsr &= ~KNN

    def set_knn_classifier(self):
        self._nsr |= KNN

    def set_classifier_type(self, classifier_type):
        if classifier_type == CLASSIFIER_RBF:
            self.set_rbf_classifier()
        elif classifier_type == CLASSIFIER_KNN:
            self.set_knn_classifier()
        else:
            raise ValueError("classifier_type must be CLASSIFIER_RBF or CLASSIFIER_KNN")

    def get_classifier_type(self):
        return CLASSIFIER_KNN if (self._nsr & KNN) else CLASSIFIER_RBF

    def set_context(self, context, norm=None, minif=None, maxif=None):
        context = int(context) & 0x7F
        norm_bit = self._context & NORM
        if norm is not None:
            if norm == NORM_L1:
                norm_bit = 0
            elif norm in (NORM_LSUP, NORM_Lsup):
                norm_bit = NORM
            else:
                raise ValueError("norm must be NORM_L1 or NORM_LSUP")
        self._context = context | norm_bit

        if minif is not None:
            self._minif = self._u16(minif)
        if maxif is not None:
            self._maxif = self._u16(maxif)
        if self._minif > self._maxif:
            raise ValueError("minif cannot be greater than maxif")

    def get_context(self):
        norm = NORM_LSUP if (self._context & NORM) else NORM_L1
        return (
            self._context & 0x7F,
            norm,
            self._minif,
            self._maxif,
        )

    def count_committed_neurons(self):
        return len(self._neurons)

    def count_total_installed_neurons(self):
        return self.network_size

    def clear_neurons(self):
        self.forget()

    def learn(self, vector, length=None, category=None):
        """Learn one vector and return the committed-neuron count.

        Supports both learn(vector, category) and learn(vector, length, category).
        """
        if category is None:
            category = length
            length = None
        if category is None:
            raise ValueError("category is required")

        category = self._u16(category)
        if category == 0:
            return len(self._neurons)

        vector = self._normalise_vector(vector, length)

        # Evaluate every context-matching committed neuron, not only RBF firings,
        # because learning needs the nearest distance when committing a neuron.
        all_matches = []
        same_category_firing = False
        for neuron in self._neurons:
            if not self._context_matches(neuron):
                continue
            distance = self._distance(vector, neuron)
            all_matches.append((distance, neuron))

            if distance < neuron[_N_AIF]:
                if (neuron[_N_CATEGORY] & 0x7FFF) == (category & 0x7FFF):
                    same_category_firing = True
                else:
                    neuron[_N_AIF] = distance
                    if neuron[_N_AIF] <= neuron[_N_MINIF]:
                        neuron[_N_AIF] = neuron[_N_MINIF]
                        neuron[_N_CATEGORY] |= 0x8000

        # Existing firing neuron of the same category already covers the vector.
        if same_category_firing:
            self._evaluate(vector)
            return len(self._neurons)

        if len(self._neurons) >= self.network_size:
            self._evaluate(vector)
            return len(self._neurons)

        min_distance = self._maxif
        if all_matches:
            min_distance = min(item[0] for item in all_matches)
            if min_distance > self._maxif:
                min_distance = self._maxif

        learned_category = category & 0x7FFF
        aif = min_distance
        if aif <= self._minif:
            aif = self._minif
            learned_category |= 0x8000

        self._neurons.append(self._new_neuron(vector, learned_category, aif))
        self._evaluate(vector)
        return len(self._neurons)

    def classify(self, vector, length=None, k=1):
        """Classify a vector.

        Returns one dictionary when k=1, otherwise a list of dictionaries.
        Each dictionary contains: nid, distance, category, degenerated.
        """
        vector = self._normalise_vector(vector, length)
        nsr = self._evaluate(vector)

        if k is None:
            k = 1
        k = max(1, int(k))
        output = []
        for item in self._results[:k]:
            output.append({
                "nid": item[2],
                "distance": item[0],
                "category": item[1] & 0x7FFF,
                "raw_category": item[1],
                "degenerated": bool(item[1] & 0x8000),
                "status": nsr,
                "identified": bool(nsr & IDN),
                "uncertain": bool(nsr & UNC),
            })

        if not output:
            unknown = {
                "nid": 0xFFFF,
                "distance": 0xFFFF,
                "category": 0xFFFF,
                "raw_category": 0xFFFF,
                "degenerated": False,
                "status": nsr,
                "identified": False,
                "uncertain": False,
            }
            return unknown if k == 1 else [unknown]

        return output[0] if k == 1 else output

    def read_neuron(self, nid):
        """Return a neuron record by zero-based chain index."""
        nid = int(nid)
        if nid < 0 or nid >= len(self._neurons):
            raise IndexError("neuron index out of range")
        neuron = self._neurons[nid]
        return {
            "nid": neuron[_N_IDENTIFIER],
            "context": neuron[_N_CONTEXT],
            "model": bytearray(neuron[_N_VECTOR]),
            "aif": neuron[_N_AIF],
            "minif": neuron[_N_MINIF],
            "category": neuron[_N_CATEGORY],
        }

    def read_neurons(self):
        """Export neurons in C++ compatible flat-record format."""
        records = []
        for neuron in self._neurons:
            records.append(neuron[_N_CONTEXT])
            records.extend(neuron[_N_VECTOR])
            records.append(neuron[_N_AIF])
            records.append(neuron[_N_MINIF])
            records.append(neuron[_N_CATEGORY])
        return records

    def write_neurons(self, neurons, ncount=None):
        """Import neurons from C++ compatible flat-record format."""
        rec_len = self.vector_size + 4
        if ncount is None:
            if len(neurons) % rec_len:
                raise ValueError("invalid neuron data length")
            ncount = len(neurons) // rec_len
        ncount = int(ncount)
        if ncount > self.network_size:
            raise ValueError("ncount exceeds network size")
        if len(neurons) < ncount * rec_len:
            raise ValueError("neuron data is incomplete")

        self.forget()
        offset = 0
        for index in range(ncount):
            context = int(neurons[offset]) & 0x7F
            model = bytearray(self.vector_size)
            for j in range(self.vector_size):
                model[j] = int(neurons[offset + 1 + j]) & 0xFF
            aif = int(neurons[offset + self.vector_size + 1])
            minif = int(neurons[offset + self.vector_size + 2])
            category = int(neurons[offset + self.vector_size + 3]) & 0xFFFF
            self._neurons.append([
                context, model, aif, minif, category, index + 1
            ])
            offset += rec_len

    # ---------------------------------------------------------
    # Register-style compatibility API
    # ---------------------------------------------------------
    def broadcast(self, vector, length=None):
        vector = self._normalise_vector(vector, length)
        self._input_buffer[:] = b"\x00" * self.vector_size
        self._input_buffer[:len(vector)] = vector
        self._last_length = len(vector)
        self._comp_index = 0
        return self._evaluate(vector)

    def read(self, reg):
        reg = int(reg) & 0xFF

        if reg == NM_NSR:
            return self._nsr & 0xFFFF
        if reg == NM_NCOUNT:
            return len(self._neurons)
        if reg == NM_MINIF:
            if self._nsr & SR and self._chain_index < len(self._neurons):
                return self._neurons[self._chain_index][_N_MINIF]
            return self._minif
        if reg == NM_MAXIF:
            if self._nsr & SR and self._chain_index < len(self._neurons):
                return self._neurons[self._chain_index][_N_AIF]
            return self._maxif
        if reg == NM_GCR:
            return self._context

        if self._nsr & SR:
            if self._chain_index >= len(self._neurons):
                return 0xFFFF
            neuron = self._neurons[self._chain_index]
            if reg == NM_NCR:
                return neuron[_N_CONTEXT]
            if reg == NM_COMP:
                if self._comp_index >= self.vector_size:
                    return 0xFFFF
                value = neuron[_N_VECTOR][self._comp_index]
                self._comp_index += 1
                return value
            if reg == NM_AIF:
                return neuron[_N_AIF]
            if reg == NM_NID:
                return neuron[_N_IDENTIFIER] & 0xFFFF
            if reg == NM_CAT:
                value = neuron[_N_CATEGORY]
                self._chain_index += 1
                self._comp_index = 0
                return value
            if reg == NM_DIST:
                return 0

        # Recognition-mode result reads.
        if reg == NM_DIST:
            if self._result_index >= len(self._results):
                return 0xFFFF
            return self._results[self._result_index][0]
        if reg == NM_CAT:
            if self._result_index >= len(self._results):
                return 0xFFFF
            item = self._results[self._result_index]
            self._top_identifier = item[2]
            self._result_index += 1
            return item[1]
        if reg == NM_NID:
            return self._top_identifier & 0xFFFF
        if reg == NM_NCR:
            return (self._top_identifier >> 16) & 0xFFFF

        return 0xFFFF

    def write(self, reg, data=0):
        reg = int(reg) & 0xFF
        data = self._u16(data)

        if reg == NM_FORGET:
            self.forget()
        elif reg == NM_RESETCHAIN:
            self.reset_chain()
        elif reg == NM_NSR:
            self._nsr = data
            self._comp_index = 0
            self._result_index = 0
            if not (self._nsr & SR):
                self._chain_index = len(self._neurons)
        elif reg == NM_GCR:
            self._context = data & 0x00FF
        elif reg == NM_MINIF:
            self._minif = data
        elif reg == NM_MAXIF:
            self._maxif = data
        elif reg == NM_INDEXCOMP:
            self._comp_index = data & 0xFF
        elif reg in (NM_COMP, NM_LCOMP):
            if self._comp_index >= self.vector_size:
                raise IndexError("component index exceeds vector size")
            self._input_buffer[self._comp_index] = data & 0xFF
            self._comp_index += 1
            if reg == NM_LCOMP:
                self._last_length = self._comp_index
                self._comp_index = 0
                self._evaluate(self._input_buffer[:self._last_length])
        elif reg == NM_CAT:
            if self._nsr & SR:
                # Low-level SR writes are intentionally limited; import complete
                # neuron records with write_neurons() for reliable operation.
                raise NotImplementedError("Use write_neurons() for SR-mode neuron import")
            self.learn(self._input_buffer[:self._last_length], category=data)
        elif reg == NM_TESTCAT:
            if self._nsr & SR:
                for neuron in self._neurons:
                    neuron[_N_CATEGORY] = data
        elif reg == NM_TESTCOMP:
            if self._nsr & SR:
                for neuron in self._neurons:
                    neuron[_N_VECTOR][self._comp_index] = data & 0xFF
                self._comp_index += 1
        return 0

    # ---------------------------------------------------------
    # C++-style method aliases
    # ---------------------------------------------------------
    Forget = forget
    ResetChain = reset_chain
    SizeNetwork = size_network
    Read = read
    Write = write
    GetUniqueID = get_unique_id
    GetVersion = get_version
    EnableL2NORM = enable_l2_norm
    DisableL2NORM = disable_l2_norm
    SetExtendedFunction = set_extended_function
    ClearExtendedFunction = clear_extended_function
    GetExtendedFunction = get_extended_function
    SetRBFClassifier = set_rbf_classifier
    SetKNNClassifier = set_knn_classifier
    SetClassifierType = set_classifier_type
    GetClassifierType = get_classifier_type
    GetContext = get_context
    SetContext = set_context
    CountCommittedNeurons = count_committed_neurons
    CountTotalInstalledNeurons = count_total_installed_neurons
    ReadNeuron = read_neuron
    ReadNeurons = read_neurons
    WriteNeurons = write_neurons
    ClearNeurons = clear_neurons
    Broadcast = broadcast
    Learn = learn
    Classify = classify


# Match the original C++ class name for simple source migration.
nmaicore = NMAICore
