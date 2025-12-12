cdef extern from "templates.hpp":

    # NOTE: Partial specialization Container<T *> exists in C++ but cannot be declared in Cython. Use specific instantiations.
    cdef cppclass Container[T]:
        T value
        T get()
        void set(T v)

    cdef cppclass Map[K, V]:
        V lookup(K key)
        void insert(K key, V value)

    cdef cppclass Container_int "Container<int>":
        int special_value
        int get_special()

    # NOTE: Template has non-type parameter 'N' (int). Cython does not support non-type template parameters. Use specific instantiations as needed.
    cdef cppclass FixedArray[T]:
        T* data
        int size()
