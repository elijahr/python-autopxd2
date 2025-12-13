# autopxd/stubs/cppregex.pxd
#
# Cython declarations for <regex> (C++11)
# Source: ISO/IEC 14882:2011 (C++11 standard)
# License: Public domain (interface declarations)
#
# Auto-imported by autopxd when regex is included.

from libcpp cimport bool
from libcpp.string cimport string

cdef extern from "<regex>" namespace "std":
    # regex_constants flags
    ctypedef int syntax_option_type
    ctypedef int match_flag_type

    cdef cppclass regex:
        regex()
        regex(const char*)
        regex(const string&)
        regex(const char*, syntax_option_type)
        regex(const string&, syntax_option_type)
        bool mark_count()

    # match_results - opaque due to template complexity
    cdef cppclass smatch:
        smatch()
        size_t size()
        bool empty()
        bool ready()
        string str()
        string str(size_t)

    cdef cppclass cmatch:
        cmatch()
        size_t size()
        bool empty()
        bool ready()

    # Algorithms
    bool regex_match(const string&, const regex&) except +
    bool regex_match(const string&, smatch&, const regex&) except +
    bool regex_search(const string&, const regex&) except +
    bool regex_search(const string&, smatch&, const regex&) except +
    string regex_replace(const string&, const regex&, const string&) except +

cdef extern from "<regex>" namespace "std::regex_constants":
    syntax_option_type icase
    syntax_option_type nosubs
    syntax_option_type optimize
    syntax_option_type collate
    syntax_option_type ECMAScript
    syntax_option_type basic
    syntax_option_type extended
    syntax_option_type awk
    syntax_option_type grep
    syntax_option_type egrep
    syntax_option_type multiline

    match_flag_type match_default
    match_flag_type match_not_bol
    match_flag_type match_not_eol
    match_flag_type match_not_bow
    match_flag_type match_not_eow
    match_flag_type match_any
    match_flag_type match_not_null
    match_flag_type match_continuous
    match_flag_type match_prev_avail
    match_flag_type format_default
    match_flag_type format_sed
    match_flag_type format_no_copy
    match_flag_type format_first_only
