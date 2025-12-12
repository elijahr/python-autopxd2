// test/real_headers/templates.hpp
// Test C++ templates for autopxd

template<typename T>
class Container {
public:
    T value;
    T get();
    void set(T v);
};

template<typename K, typename V>
class Map {
public:
    V lookup(K key);
    void insert(K key, V value);
};

template<>
class Container<int> {
public:
    int special_value;
    int get_special();
};
