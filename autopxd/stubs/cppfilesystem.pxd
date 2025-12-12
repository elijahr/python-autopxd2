# autopxd/stubs/cppfilesystem.pxd
#
# Cython declarations for <filesystem> (C++17)
# Source: ISO/IEC 14882:2017 (C++17 standard)
# License: Public domain (interface declarations)
#
# Auto-imported by autopxd when filesystem is included.

from libcpp cimport bool
from libcpp.string cimport string
from libc.stdint cimport uintmax_t

cdef extern from "<filesystem>" namespace "std::filesystem":
    cdef cppclass path:
        path()
        path(const char*)
        path(const string&)

        string string()
        const char* c_str()

        path filename()
        path stem()
        path extension()
        path parent_path()
        path root_path()

        bool empty()
        bool has_filename()
        bool has_extension()
        bool has_parent_path()

        path operator/(const path&)

    cdef cppclass directory_entry:
        directory_entry()
        directory_entry(const path&)

        const path& path()
        bool exists()
        bool is_regular_file()
        bool is_directory()
        bool is_symlink()
        uintmax_t file_size()

    cdef cppclass directory_iterator:
        directory_iterator()
        directory_iterator(const path&)

    # Free functions
    bool exists(const path&)
    bool is_regular_file(const path&)
    bool is_directory(const path&)
    bool is_symlink(const path&)

    bool create_directory(const path&)
    bool create_directories(const path&)
    bool remove(const path&)
    uintmax_t remove_all(const path&)
    void rename(const path&, const path&)
    void copy(const path&, const path&)
    void copy_file(const path&, const path&)

    path current_path()
    void current_path(const path&)
    path absolute(const path&)
    path canonical(const path&)

    uintmax_t file_size(const path&)
