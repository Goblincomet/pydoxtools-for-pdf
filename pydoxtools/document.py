import mimetypes
from functools import cached_property
from pathlib import Path
from typing import IO
from urllib.parse import urlparse

import langdetect
import numpy as np
import pandas as pd
import requests
import yaml

from .document_base import Pipeline, ElementType
from .extract_classes import LanguageExtractor, TextBlockClassifier
from .extract_files import FileLoader
from .extract_html import HtmlExtractor
from .extract_index import IndexExtractor, KnnQuery, \
    SimilarityGraph, TextrankOperator, TextPieceSplitter
from .extract_nlpchat import OpenAIChat
from .extract_objects import EntityExtractor
from .extract_ocr import OCRExtractor
from .extract_pandoc import PandocLoader, PandocOperator, PandocConverter, PandocBlocks
from .extract_spacy import SpacyOperator, extract_spacy_token_vecs, get_spacy_embeddings, extract_noun_chunks
from .extract_tables import ListExtractor, TableCandidateAreasExtractor
from .extract_textstructure import DocumentElementFilter, TextBoxElementExtractor, TitleExtractor
from .html_utils import get_text_only_blocks
from .list_utils import flatten, flatten_dict, deep_str_convert
from .nlp_utils import calculate_string_embeddings
from .operators import Alias, LambdaOperator, ElementWiseOperator, Configuration, Constant
from .pdf_utils import PDFFileLoader
from .operator_huggingface import QamExtractor


def is_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


class DocumentTypeError(Exception):
    pass


class Document(Pipeline):
    """This class implements an extensive pipeline using the [][document_base.Pipeline] class
for information extraction from documents.

***

In order to load a document, simply
open it with the document class::

    from pydoxtools import Document
    doc = Document(fobj=./data/demo.docx)

You can then access any extracted data by
calling x with the specified member::

    doc.x("addresses")
    doc.x("entities")
    doc.x("full_text")
    # etc...

Most members are also callable like a normal
class member in order to make the code easier to read::

    doc.addresses

A list of all available extraction data
can be called like this::

    doc.x_funcs()

***

The document class is backed by a *pipeline* class with a pre-defined pipeline focusing on
document extraction tasks. This extraction pipeline can be overwritten partially or completly replaced.
In order to customize the pipeline it is usually best to take the pipeline for
basic documents defined in pydoxtools.Document as a starting point and
only overwrite the parts that should be customized.

inherited classes can override any part of the graph.

It is possible to exchange/override/extend or introduce extraction pipelines for individual file types (including
the generic one: "*") such as *.html extractors, *.pdf, *.txt etc..

Strings inside a document class indicate the inclusion of that document type pipeline but with a lower priority
this way a directed extraction graph gets built. This only counts for the current class that is
being defined though!!

Example extension pipeline for an OCR extractor which converts images into text
"image" code block and supports filetypes: ".png", ".jpeg", ".jpg", ".tif", ".tiff"::

    "image": [
            OCRExtractor()
            .pipe(file="raw_content")
            .out("ocr_pdf_file")
            .cache(),
        ],
    # the first base doc types have priority over the last ones
    # so here .png > image > .pdf
    ".png": ["image", ".pdf"],
    ".jpeg": ["image", ".pdf"],
    ".jpg": ["image", ".pdf"],
    ".tif": ["image", ".pdf"],
    ".tiff": ["image", ".pdf"],
    # the "*" gets overwritten by functions above
    "*": [...]

Each function (or node) in the extraction pipeline gets connected to other nodes in the pipeline
by the "pipe" command.

These arguments can be overwritten by a new pipeline in inherited documents or document types
that are higher up in the hierarchy. The argument precedence is hereby as follows::

    python-class-member < extractor-graph-function < configuration

when creating a new pipeline for documentation purposes a general rule is:
if the operation is too complicated to be self-describing, then use a function or class
and put the documentation in there. A Lambda function is not the right tool in this case.

"""

    """
    TODO: One can also change the configuration of individual operators. For example
    of the Table Operator or Space models...

    TODO: add "extension/override" logic for individual file types. The main important thing there is
          to make sure we don't have any "dangling" functions left over when filetype logics
          gets overwritten
    """

    # TODO: rename extractors to operators
    _extractors = {
        ".pdf": [
            FileLoader()  # pdfs are usually in binary format...
            .pipe(fobj="_fobj").out("raw_content").cache(),
            PDFFileLoader()
            .pipe(fobj="raw_content", page_numbers="_page_numbers", max_pages="_max_pages")
            .out("pages_bbox", "elements", "meta", pages="page_set")
            .cache(),
            LambdaOperator(lambda pages: len(pages))
            .pipe(pages="page_set").out("num_pages").cache(),
            DocumentElementFilter(element_type=ElementType.Line)
            .pipe("elements").out("line_elements").cache(),
            DocumentElementFilter(element_type=ElementType.Graphic)
            .pipe("elements").out("graphic_elements").cache(),
            ListExtractor().cache()
            .pipe("line_elements").out("lists"),
            TableCandidateAreasExtractor()
            .pipe("graphic_elements", "line_elements", "pages_bbox", "text_box_elements", "filename")
            .out("table_candidates", box_levels="table_box_levels").cache(),
            LambdaOperator(lambda candidates: [t.df for t in candidates if t.is_valid])
            .pipe(candidates="table_candidates").out("table_df0").cache(),
            LambdaOperator(lambda table_df0, lists: table_df0 + [lists]).cache()
            .pipe("table_df0", "lists").out("tables_df"),
            TextBoxElementExtractor()
            .pipe("line_elements").out("text_box_elements").cache(),
            LambdaOperator(lambda df: df.get("text", None).to_list())
            .pipe(df="text_box_elements").out("text_box_list").cache(),
            LambdaOperator(lambda tb: "\n\n".join(tb))
            .pipe(tb="text_box_list").out("full_text").cache(),
            TitleExtractor()
            .pipe("line_elements").out("titles", "side_titles").cache(),
            LanguageExtractor().cache()
            .pipe(text="full_text").out("language").cache()
        ],
        ".html": [
            HtmlExtractor()
            .pipe(raw_html="raw_content", url="source")
            .out("main_content_clean_html", "summary", "language", "goose_article",
                 "main_content", "schemadata", "final_urls", "pdf_links", "title",
                 "short_title", "url", tables="tables_df", html_keywords="html_keywords_str").cache(),
            LambdaOperator(lambda article: article.links)
            .pipe(article="goose_article").out("urls").cache(),
            LambdaOperator(lambda article: article.top_image)
            .pipe(article="goose_article").out("main_image").cache(),
            Alias(full_text="main_content"),
            LambdaOperator(lambda x: pd.DataFrame(get_text_only_blocks(x), columns=["text"])).cache()
            .pipe(x="raw_content").out("text_box_elements"),
            LambdaOperator(lambda t, s: [t, s])
            .pipe(t="title", s="short_title").out("titles").cache(),
            LambdaOperator(lambda x: set(w.strip() for w in x.split(",")))
            .pipe(x="html_keywords_str").out("html_keywords"),

            ########### AGGREGATION ##############
            LambdaOperator(lambda **kwargs: set(flatten(kwargs.values())))
            .pipe("html_keywords", "textrank_keywords").out("keywords").cache(),
        ],
        ".docx": ["pandoc"],
        ".odt": ["pandoc"],
        ".md": ["pandoc"],
        ".rtf": ["pandoc"],
        ".epub": ["pandoc"],
        ".markdown": ["pandoc"],
        "pandoc": [
            PandocLoader()
            .pipe(raw_content="raw_content", document_type="document_type")
            .out("pandoc_document").cache(),
            Configuration(output_format="markdown"),
            PandocConverter()
            .pipe("output_format", pandoc_document="pandoc_document")
            .out("full_text").cache(),
            PandocBlocks()
            .pipe(pandoc_document="pandoc_document").out("pandoc_blocks").cache(),
            PandocOperator(method="headers")
            .pipe(pandoc_blocks="pandoc_blocks").out("headers").cache(),
            PandocOperator(method="tables_df")
            .pipe(pandoc_blocks="pandoc_blocks").out("tables_df").cache(),
            PandocOperator(method="lists")
            .pipe(pandoc_blocks="pandoc_blocks").out("lists").cache(),
        ],
        "image": [
            # add a "base-document" type (.pdf) images get converted into pdfs
            # and then further processed from there
            ".pdf",  # as we are extracting a pdf we would like to use the pdf functions...
            Configuration(ocr_lang="auto", ocr_on=True),
            OCRExtractor()
            .pipe("ocr_on", "ocr_lang", file="raw_content")
            .out("ocr_pdf_file"),
            # we need to do overwrite the pdf loading for images we inherited from
            # the ".pdf" logic as we are
            # now taking the pdf from a different variable
            PDFFileLoader()
            .pipe(fobj="ocr_pdf_file")
            .out("pages_bbox", "elements", "meta", pages="page_set")
            .cache(),
        ],
        # the first base doc types have priority over the last ones
        # so here .png > image > .pdf
        ".png": ["image", ".pdf"],
        ".jpeg": ["image", ".pdf"],
        ".jpg": ["image", ".pdf"],
        ".tif": ["image", ".pdf"],
        ".tiff": ["image", ".pdf"],
        ".yaml": [
            "dict",
            Alias(full_text="raw_content"),
            LambdaOperator(lambda x: dict(data=yaml.unsafe_load(x)))
            .pipe(x="full_text").out("data").cache()
            # TODO: we might need to have a special "result" message, that we
            #       pass around....
        ],
        "dict": [  # pipeline to handle data based documents
            Alias(raw_content="_fobj"),
            Alias(data="raw_content"),
            LambdaOperator(lambda x: yaml.dump(deep_str_convert(x)))
            .pipe("data").out("full_text"),
            LambdaOperator(lambda x: [str(k) + ": " + str(v) for k, v in flatten_dict(a.data).items()])
            .pipe(x="data").out("text_box_elements").cache(),
            Alias(text_box_list="text_box_elements"),
            Alias(text_segments="text_box_elements"),
        ],
        # TODO: json, csv etc...
        # TODO: pptx, odp etc...
        "*": [
            # Loading text files
            FileLoader()
            .pipe(fobj="_fobj", document_type="document_type", page_numbers="_page_numbers", max_pages="_max_pages")
            .out("raw_content").cache(),
            Alias(full_text="raw_content"),

            ## Standard text splitter for splitting text along lines...
            LambdaOperator(lambda x: pd.DataFrame(x.split("\n\n"), columns=["text"]))
            .pipe(x="full_text").out("text_box_elements").cache(),
            LambdaOperator(lambda df: df.get("text", None).to_list())
            .pipe(df="text_box_elements").out("text_box_list").cache(),
            # TODO: replace this with a real, generic table detection
            #       e.g. running the text through pandoc or scan for html tables
            Constant(tables_df=[]),
            LambdaOperator(lambda tables_df: [df.to_dict('index') for df in tables_df]).cache()
            .pipe("tables_df").out("tables_dict"),
            Alias(tables="tables_dict"),
            TextBlockClassifier()
            .pipe("text_box_elements").out("addresses").cache(),

            ## calculate some metadata values
            LambdaOperator(lambda full_text: 1 + (len(full_text) // 1000))
            .pipe("full_text").out("num_pages").cache(),
            LambdaOperator(lambda full_text: len(full_text.split()))
            .pipe("full_text").out("num_words").cache(),
            LambdaOperator(lambda spacy_sents: len(spacy_sents))
            .pipe("spacy_sents").out("num_sents"),
            LambdaOperator(lambda ft: sum(1 for c in ft if c.isdigit()) / sum(1 for c in ft if c.isalpha()))
            .pipe(ft="full_text").out("a_d_ratio").cache(),
            LambdaOperator(lambda full_text: langdetect.detect(full_text))
            .pipe("full_text").out("language").cache(),

            #########  SPACY WRAPPERS  #############
            Configuration(spacy_model_size="md", spacy_model="auto"),
            SpacyOperator()
            .pipe("full_text", "language", "spacy_model", model_size="spacy_model_size")
            .out(doc="spacy_doc", nlp="spacy_nlp").cache(),
            LambdaOperator(extract_spacy_token_vecs)
            .pipe("spacy_doc").out("spacy_vectors"),
            LambdaOperator(get_spacy_embeddings)
            .pipe("spacy_nlp").out("spacy_embeddings"),
            LambdaOperator(lambda spacy_doc: list(spacy_doc.sents))
            .pipe("spacy_doc").out("spacy_sents"),
            LambdaOperator(extract_noun_chunks)
            .pipe("spacy_doc").out("spacy_noun_chunks").cache(),
            ########## END OF SPACY ################

            EntityExtractor().cache()
            .pipe("spacy_doc").out("entities"),
            # TODO: try to implement as much as possible from the constants below for all documentypes
            #       summary, urls, main_image, keywords, final_url, pdf_links, schemadata, tables_df
            # TODO: implement summarizer based on textrank
            Alias(url="source"),

            ########### VECTORIZATION ##########
            Alias(sents="spacy_sents"),
            Alias(noun_chunks="spacy_noun_chunks"),

            LambdaOperator(lambda x: x.vector)
            .pipe(x="spacy_doc").out("vector").cache(),
            LambdaOperator(
                lambda x: dict(
                    sent_vecs=np.array([e.vector for e in x]),
                    sent_ids=list(range(len(x)))))
            .pipe(x="sents").out("sent_vecs", "sent_ids").cache(),
            LambdaOperator(
                lambda x: dict(
                    noun_vecs=np.array([e.vector for e in x]),
                    noun_ids=list(range(len(x)))))
            .pipe(x="noun_chunks").out("noun_vecs", "noun_ids").cache(),

            ########### SEGMENT_INDEX ##########
            TextPieceSplitter()
            .pipe(full_text="full_text").out("text_segments").cache(),
            Configuration(
                text_segment_model="deepset/minilm-uncased-squad2",
                text_segment_only_tokenizer=True
            ),
            ElementWiseOperator(calculate_string_embeddings, return_iterator=False)
            .pipe(
                elements="text_segments",
                model_id="text_segment_model",
                only_tokenizer="text_segment_only_tokenizer")
            .out("text_segment_vectors"),

            ########### NOUN_INDEX #############
            IndexExtractor()
            .pipe(vecs="noun_vecs", ids="noun_ids").out("noun_index").cache(),
            LambdaOperator(lambda spacy_nlp: lambda x: spacy_nlp(x).vector)
            .pipe("spacy_nlp").out("vectorizer").cache(),
            KnnQuery().pipe(index="noun_index", idx_values="noun_chunks", vectorizer="vectorizer")
            .out("noun_query").cache(),
            SimilarityGraph().pipe(index_query_func="noun_query", source="noun_chunks")
            .out("noun_graph").cache(),
            Configuration(top_k_text_rank_keywords=5),
            TextrankOperator()
            .pipe(top_k="top_k_text_rank_keywords", G="noun_graph").out("textrank_keywords").cache(),
            # TODO: we will probably get better keywords if we first get the most important sentences or
            #       a summary and then exract keywords from there :).
            Alias(keywords="textrank_keywords"),
            ########### END NOUN_INDEX ###########

            ########### SENTENCE_INDEX ###########
            IndexExtractor()
            .pipe(vecs="sent_vecs", ids="sent_ids").out("sent_index").cache(),
            LambdaOperator(lambda spacy_nlp: lambda x: spacy_nlp(x).vector)
            .pipe("spacy_nlp").out("vectorizer").cache(),
            KnnQuery().pipe(index="sent_index", idx_values="spacy_sents", vectorizer="vectorizer")
            .out("sent_query").cache(),
            SimilarityGraph().pipe(index_query_func="sent_query", source="spacy_sents")
            .out("sent_graph").cache(),
            Configuration(top_k_text_rank_sentences=5),
            TextrankOperator()
            .pipe(top_k="top_k_text_rank_sentences", G="sent_graph").out("textrank_sents").cache(),

            ########### QaM machine #############
            # TODO: make sure we can set the model that we want to use dynamically!
            Configuration(qam_model_id='deepset/minilm-uncased-squad2'),
            QamExtractor()
            .pipe("property_dict", trf_model_id="qam_model_id").out("answers").cache(),

            ########### Chat AI ##################
            Configuration(openai_chat_model_id="gpt-3.5-turbo"),
            OpenAIChat().pipe("property_dict", model_id="openai_chat_model_id")
            .out("chat_answers").cache()
        ]
    }

    def __init__(
            self,
            # TODO: move most of this into document-specific pipeline
            fobj: str | bytes | Path | IO = None,
            source: str | Path = None,
            page_numbers: list[int] = None,
            max_pages: int = None,
            mime_type: str = None,
            filename: str = None,
            document_type: str = None
            # TODO: add "auto" for automatic recognition of the type using python-magic
    ):
        """
        fobj: a file object which should be loaded.
            - if it is a string or bytes object:   the string itself is the document!
            - if it is a pathlib.Path: load the document from the path
            - if it is a file object: load document from file object (or bytestream  etc...)
        source: Where does the extracted data come from? (Examples: URL, 'pdfupload', parent-URL, or a path)"
        page_numbers: list of the specific pages that we would like to extract (for example in a pdf)
        max_pages: maximum number of pages that we want to extract in order to protect resources
        mime_type: optional mimetype for the document
        filename: optional filename. Helps sometimes helps in determining the purpose of a document
        document_type: directly specify the document type which specifies the extraction
            logic that should be used
        """

        super().__init__()

        # TODO: move this code into its own little extractor...
        try:
            if is_url(fobj):
                response = requests.get(fobj)
                with open('file.pdf', 'wb') as file:
                    fobj = response.content
        except:
            pass

        self._fobj = fobj  # file object
        self._source = source or "unknown"
        self._document_type = document_type
        self._mime_type = mime_type
        self._filename = filename
        self._page_numbers = page_numbers
        self._max_pages = max_pages

    @cached_property
    def filename(self) -> str | None:
        """TODO: move this into document pipeline"""
        if hasattr(self._fobj, "name"):
            return self._fobj.name
        elif isinstance(self._fobj, Path):
            return self._fobj.name
        elif self._filename:
            return self._filename
        else:
            return None

    @cached_property
    def path(self):
        if isinstance(self._fobj, Path):
            return self._fobj
        else:
            return self.source

    @cached_property
    def document_type(self):
        """
        detect doc type based on file-ending
        TODO add a doc-type extractor using for example python-magic
        """
        try:
            if self._document_type:
                return self._document_type
            elif self._mime_type:
                return mimetypes.guess_extension(self._mime_type)
            # get type from path suffix
            elif isinstance(self._fobj, Path):
                if self._fobj.exists():
                    return self._fobj.suffix
                elif hasattr(self._fobj, "name"):
                    return Path(self._fobj.name).suffix
            elif isinstance(self._fobj, str) and (self._document_type is None):
                return "generic"

            # for example if it is a string without a type
            # TODO: detect type with python-magic here...
            raise DocumentTypeError(f"Could not find the document type for {self._fobj[-100:]} ...")
        except:
            try:
                raise DocumentTypeError(f"Could not detect document type for {self._fobj} ...")
            except:
                raise DocumentTypeError(f"Could not detect document type for {self._fobj[-100:]} ...")

    @cached_property
    def pipeline_chooser(self):
        if self.document_type in self._x_funcs:
            return self.document_type
        else:
            return "*"

    @property
    def source(self) -> str:
        return self._source

    @property
    def fobj(self):
        return self._fobj

    """
    @property
    def final_url(self) -> list[str]:
        ""sometimes, a document points to a url itself (for example a product webpage) and provides
        a link where this document can be found. And this url does not necessarily have to be the same as the source
        of the document.""
        return []

    @property
    def parent(self) -> list[str]:
        ""sources that embed this document in some way (for example as a link)
        (for example a product page which embeds
        a link to this document (e.g. a datasheet)
        ""
        return []
    """
