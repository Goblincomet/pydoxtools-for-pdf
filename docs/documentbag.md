# [pydoxtools.DocumentBag][]

::: pydoxtools.DocumentBag

## Text extraction attributes and functions

The [pydoxtools.DocumentBag][] is built
on the [pydoxtools.Pipeline][] class and most of the text extraction
functionality makes extensive use of the pipeline features. All attributes
and functions that are created by the pipeline are documented here.

Pipeline visualizations for the structure of the Document pipelines for different
document types can be found [here](https://github.com/Xyntopia/pydoxtools/tree/gh-pages/images).


### doc_configuration
            
We can pass through a configuration object to Documents that are created in our document bag. Any setting that is supported by Document can be specified here.

Can be called using:

    <DocumentBag>.x('doc_configuration')
    # or
    <DocumentBag>.doc_configuration

return type
: typing.Any

supports pipeline flows:
: *, <class 'dask.bag.core.Bag'\>, <class 'list'\>, <class 'pathlib.Path'\>, <class 'pydoxtools.document.DatabaseSource'\>

### forgiving_extracts
            
When enabled, if we execute certain batch operations on our document bag, this will not stop the extraction, but rather put an error message in the document.

Can be called using:

    <DocumentBag>.x('forgiving_extracts')
    # or
    <DocumentBag>.forgiving_extracts

return type
: typing.Any

supports pipeline flows:
: *, <class 'dask.bag.core.Bag'\>, <class 'list'\>, <class 'pathlib.Path'\>, <class 'pydoxtools.document.DatabaseSource'\>

### _stats
            
A constant value

Can be called using:

    <DocumentBag>.x('_stats')
    # or
    <DocumentBag>._stats

return type
: typing.Any

supports pipeline flows:
: *, <class 'dask.bag.core.Bag'\>, <class 'list'\>, <class 'pathlib.Path'\>, <class 'pydoxtools.document.DatabaseSource'\>

### verbosity
            
Configuration for values:

* verbosity = None (default)

Can be called using:

    <DocumentBag>.x('verbosity')
    # or
    <DocumentBag>.verbosity

return type
: typing.Any

supports pipeline flows:
: *, <class 'dask.bag.core.Bag'\>, <class 'list'\>, <class 'pathlib.Path'\>, <class 'pydoxtools.document.DatabaseSource'\>

### get_dicts
            
Returns a function closure which returns a bag of the specified
    property of the enclosed documents.

Can be called using:

    <DocumentBag>.x('get_dicts')
    # or
    <DocumentBag>.get_dicts

return type
: typing.Callable[[typing.Any], dask.bag.core.Bag]

supports pipeline flows:
: *, <class 'dask.bag.core.Bag'\>, <class 'list'\>, <class 'pathlib.Path'\>, <class 'pydoxtools.document.DatabaseSource'\>

### d
            
Alias for: 

* get_dicts->d (output)

Can be called using:

    <DocumentBag>.x('d')
    # or
    <DocumentBag>.d

return type
: typing.Any

supports pipeline flows:
: *, <class 'dask.bag.core.Bag'\>, <class 'list'\>, <class 'pathlib.Path'\>, <class 'pydoxtools.document.DatabaseSource'\>

### bag_apply
            
Basically it applies a function element-wise
    on documents in a dask bag and then creates a new DocumentBag from that. This
    works similar to pandas dataframes and series. But with documents
    as a basic datatype. And apply functions are also required to
    produce data which can be used as a document again (which is a lot).

Can be called using:

    <DocumentBag>.x('bag_apply')
    # or
    <DocumentBag>.bag_apply

return type
: typing.Callable[..., dask.bag.core.Bag]

supports pipeline flows:
: *, <class 'dask.bag.core.Bag'\>, <class 'list'\>, <class 'pathlib.Path'\>, <class 'pydoxtools.document.DatabaseSource'\>

### apply
            
Basically it creates a Documentbag from two sets of
    on documents in a dask bag and then creates a new DocumentBag from that. This
    works similar to pandas dataframes and series. But with documents
    as a basic datatype. And apply functions are also required to
    produce data which can be used as a document again (which is a lot).

Can be called using:

    <DocumentBag>.x('apply')
    # or
    <DocumentBag>.apply

return type
: typing.Callable[..., pydoxtools.document.DocumentBag]

supports pipeline flows:
: *, <class 'dask.bag.core.Bag'\>, <class 'list'\>, <class 'pathlib.Path'\>, <class 'pydoxtools.document.DatabaseSource'\>

### exploded
            


Can be called using:

    <DocumentBag>.x('exploded')
    # or
    <DocumentBag>.exploded

return type
: typing.Callable[..., pydoxtools.document.DocumentBag]

supports pipeline flows:
: *, <class 'dask.bag.core.Bag'\>, <class 'list'\>, <class 'pathlib.Path'\>, <class 'pydoxtools.document.DatabaseSource'\>

### e
            
Alias for: 

* exploded->e (output)

Can be called using:

    <DocumentBag>.x('e')
    # or
    <DocumentBag>.e

return type
: typing.Any

supports pipeline flows:
: *, <class 'dask.bag.core.Bag'\>, <class 'list'\>, <class 'pathlib.Path'\>, <class 'pydoxtools.document.DatabaseSource'\>

### stats
            
gather a number of statistics from documents as a pandas dataframe

Can be called using:

    <DocumentBag>.x('stats')
    # or
    <DocumentBag>.stats

return type
: typing.Any

supports pipeline flows:
: *, <class 'dask.bag.core.Bag'\>, <class 'list'\>, <class 'pathlib.Path'\>, <class 'pydoxtools.document.DatabaseSource'\>

### Document
            
Get a factory for pre-configured documents. Can be called just like [pydoxtools.Document][] class, but automatically gets assigned the same configuration as all Documents in this bag

Can be called using:

    <DocumentBag>.x('Document')
    # or
    <DocumentBag>.Document

return type
: typing.Any

supports pipeline flows:
: *, <class 'dask.bag.core.Bag'\>, <class 'list'\>, <class 'pathlib.Path'\>, <class 'pydoxtools.document.DatabaseSource'\>

### vectorizer
            
vectorizes a query, using the document configuration of the Documentbag to determine which model to use.

Can be called using:

    <DocumentBag>.x('vectorizer')
    # or
    <DocumentBag>.vectorizer

return type
: typing.Any

supports pipeline flows:
: *, <class 'dask.bag.core.Bag'\>, <class 'list'\>, <class 'pathlib.Path'\>, <class 'pydoxtools.document.DatabaseSource'\>

### add_to_chroma
            
in order to build an index in chrome db we need a key, text, embeddings and a key. Those come from a daskbag with dictionaries with those keys. pydoxtools will return two functions which will - create the index- query the index

Can be called using:

    <DocumentBag>.x('add_to_chroma')
    # or
    <DocumentBag>.add_to_chroma

return type
: typing.Any

supports pipeline flows:
: *, <class 'dask.bag.core.Bag'\>, <class 'list'\>, <class 'pathlib.Path'\>, <class 'pydoxtools.document.DatabaseSource'\>

### docs
            
create a bag with one document for each file that was foundFrom this point we can hand off the logic to str(Bag) pipeline.

Can be called using:

    <DocumentBag>.x('docs')
    # or
    <DocumentBag>.docs

return type
: <class 'dask.bag.core.Bag'\> | typing.Any

supports pipeline flows:
: <class 'dask.bag.core.Bag'\>, <class 'list'\>, <class 'pathlib.Path'\>, <class 'pydoxtools.document.DatabaseSource'\>

### take
            
No documentation

Can be called using:

    <DocumentBag>.x('take')
    # or
    <DocumentBag>.take

return type
: typing.Any

supports pipeline flows:
: <class 'dask.bag.core.Bag'\>, <class 'list'\>, <class 'pathlib.Path'\>, <class 'pydoxtools.document.DatabaseSource'\>

### compute
            
No documentation

Can be called using:

    <DocumentBag>.x('compute')
    # or
    <DocumentBag>.compute

return type
: typing.Any

supports pipeline flows:
: <class 'dask.bag.core.Bag'\>, <class 'list'\>, <class 'pathlib.Path'\>, <class 'pydoxtools.document.DatabaseSource'\>

### sql
            
No documentation

Can be called using:

    <DocumentBag>.x('sql')
    # or
    <DocumentBag>.sql

return type
: typing.Any

supports pipeline flows:
: <class 'pydoxtools.document.DatabaseSource'\>

### connection_string
            
No documentation

Can be called using:

    <DocumentBag>.x('connection_string')
    # or
    <DocumentBag>.connection_string

return type
: typing.Any

supports pipeline flows:
: <class 'pydoxtools.document.DatabaseSource'\>

### index_column
            
No documentation

Can be called using:

    <DocumentBag>.x('index_column')
    # or
    <DocumentBag>.index_column

return type
: typing.Any

supports pipeline flows:
: <class 'pydoxtools.document.DatabaseSource'\>

### bytes_per_chunk
            
Configuration for values:

* bytes_per_chunk = 256 MiB (default)

Can be called using:

    <DocumentBag>.x('bytes_per_chunk')
    # or
    <DocumentBag>.bytes_per_chunk

return type
: typing.Any

supports pipeline flows:
: <class 'pydoxtools.document.DatabaseSource'\>

### dataframe
            
Load a table using dask/pandas read_sql

    sql: can either be the entire table or an SQL expression

Can be called using:

    <DocumentBag>.x('dataframe')
    # or
    <DocumentBag>.dataframe

return type
: <class 'dask.dataframe.core.DataFrame'\>

supports pipeline flows:
: <class 'pydoxtools.document.DatabaseSource'\>

### bag
            
create a dask bag with all the filepaths in it

Can be called using:

    <DocumentBag>.x('bag')
    # or
    <DocumentBag>.bag

return type
: typing.Any

supports pipeline flows:
: <class 'list'\>, <class 'pathlib.Path'\>, <class 'pydoxtools.document.DatabaseSource'\>

### root_path
            
Alias for: 

* source->root_path (output)

Can be called using:

    <DocumentBag>.x('root_path')
    # or
    <DocumentBag>.root_path

return type
: typing.Any

supports pipeline flows:
: <class 'list'\>, <class 'pathlib.Path'\>

### paths
            


Can be called using:

    <DocumentBag>.x('paths')
    # or
    <DocumentBag>.paths

return type
: typing.Callable

supports pipeline flows:
: <class 'list'\>, <class 'pathlib.Path'\>

### file_path_list
            
No documentation

Can be called using:

    <DocumentBag>.x('file_path_list')
    # or
    <DocumentBag>.file_path_list

return type
: <class 'dask.bag.core.Bag'\> | typing.Any

supports pipeline flows:
: <class 'list'\>, <class 'pathlib.Path'\>

### dir_list
            
No documentation

Can be called using:

    <DocumentBag>.x('dir_list')
    # or
    <DocumentBag>.dir_list

return type
: <class 'dask.bag.core.Bag'\> | typing.Any

supports pipeline flows:
: <class 'list'\>, <class 'pathlib.Path'\>