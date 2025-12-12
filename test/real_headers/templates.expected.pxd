cdef extern from "templates.hpp":

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
