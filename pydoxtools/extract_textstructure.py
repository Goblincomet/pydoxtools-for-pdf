from __future__ import annotations  # this is so, that we can use python3.10 annotations..

import operator
import typing
from dataclasses import asdict, fields

import numpy as np
import pandas as pd
import pdfminer
from pdfminer.layout import LTTextLineVertical
from sklearn.ensemble import IsolationForest

import pydoxtools.operators_base
from pydoxtools import document_base
from . import cluster_utils
from . import list_utils


def _line2txt(LTOBJ: typing.Iterable, size_hints=False):
    """
    extract text from pdfiner.six lineobj including size hints

    TODO: speedup using cython/nuitka/numba
    """
    txt = ""
    last_size = 0
    for i, ch in enumerate(LTOBJ):
        newtxt = ""
        sizehint = ""
        if isinstance(ch, pdfminer.layout.LTText):
            newtxt = ch.get_text()
        if size_hints:
            if isinstance(ch, pdfminer.layout.LTChar):
                newsize = ch.size
                if i > 0:
                    if newsize < last_size:
                        sizehint = "<s>"
                    elif newsize > last_size:
                        sizehint = "</s>"
                last_size = newsize
        txt += sizehint + newtxt
    return txt


def docinfo(self) -> list[dict[str, str]]:
    """list of document metadata such as author, creation date, organization"""
    return []


def num_pages(self) -> int:
    return len(self.pages)


def pages(self) -> list[str]:
    """automatically divide text into approx. pages"""
    page_word_size = 500
    words = self.full_text.split()
    # for i in range(len(words)):
    pages = list(words[i:i + page_word_size] for i in range(0, len(words), page_word_size))
    return pages


def mime_type(self) -> str:
    """
    type such as "pdf", "html" etc...  can also be the mimetype!
    TODO: maybe we can do something generic here?
    """
    return "unknown"


# TODO: Maybe move title detection and similar things into this function as well?
def extract_text_elements(text: str) -> list[document_base.DocumentElement]:
    # we should also make sure, if its possible or us to detect any sort of ASCII
    # or pandoc tables here...
    elements = [document_base.DocumentElement(
        type=document_base.ElementType.TextBox,
        text=tb,
        place_holder_text=f"textblock{i}",
        level=1,
        p_num=0
    ) for i, tb in enumerate(text.split("\n\n"))]

    return elements


class DocumentElementFilter(pydoxtools.operators_base.Operator):
    """Filter document elements for various criteria"""

    def __init__(self, element_type: document_base.ElementType):
        super().__init__()
        self.element_type = element_type

    def __call__(
            self, elements: list[pydoxtools.document_base.DocumentElement]
    ) -> list[pydoxtools.document_base.DocumentElement]:
        df = [e for e in elements if e.type == self.element_type]
        return df


def group_elements(elements: pd.DataFrame, by: list[str], agg: str):
    group = elements.groupby(by)
    if agg == "boxes_from_lines_w_bb":
        # aggregate object from the same box and calculate new
        # bounding boxes, also join the formatted text
        bg = group.agg(
            x0=("x0", "min"), y0=("y0", "min"),
            x1=("x1", "max"), y1=("y1", "max"),
            tmp_text=("obj",
                      lambda x: "".join(_line2txt(obj, size_hints=False) if obj else "" for obj in x.values)),
            text=("rawtext", "sum")
        )
        # overlay text with tmp_text wherever we were able to construct a "tmp_text" object
        tmp_text_selector = bg.tmp_text.str.len() > 0
        bg.loc[tmp_text_selector, "text"] = bg.loc[tmp_text_selector, "tmp_text"]
        bg.drop(columns=['tmp_text'])
        # strip whitespace from boxes
        bg["text"] = bg["text"].str.strip()
        # remove empty box_groups
        bg = bg[bg.text.str.len() > 0].copy()
        return bg
    elif "sections":
        group = elements.explode('sections').groupby(*by)
        df = group.agg(text=("rawtext", "sum"), order=("boxnum", "min")).sort_values("order")

        return df["text"].to_dict()


def text_boxes_from_elements(line_elements: list[document_base.DocumentElement]) -> dict[str, pd.DataFrame | None]:
    """
    # TODO: get rid of this function.... too many levels

    create textboxes and create bounding boxes and aggregated text from
    a pandas dataframe with textlines.
    returns a list of textboxes together wth some coordinate data and
    the contained text.

    TODO: generalize this function into an "aggregator" function

    TODO: make it possible to use alternative distance metrics to generate
          the text boxes...

    TODO: detect textboxes if they weren't loaded from another framewok
          already (for example pdfminer.six automatically detects textboxes ad
          we save them in the elements array)

    TODO: do some schema validation on the pandas dataframes...
    """

    df = pd.DataFrame(line_elements)
    bg = group_elements(df, ['p_num', 'boxnum'], agg="boxes_from_lines_w_bb")
    tbs = bg.apply(lambda x: document_base.DocumentElement(
        type=document_base.ElementType.TextBox,
        text=x.text,
        level=1,
        p_num=x.name[0],
        boxnum=x.name[1],
        x0=x.x0, y0=x.y0, x1=x.x1, y1=x.y1,
    ), axis=1).to_list()
    return dict(text_box_elements=tbs)


class SectionsExtractor(pydoxtools.operators_base.Operator):
    """
    extract sections from a textbox dataframe
    """

    def __call__(self, elements: list[document_base.DocumentElement]):
        df = pd.DataFrame(elements)
        bg = group_elements(df, ['sections'], agg="sections")
        return {"sections": bg}


class TitleExtractor(pydoxtools.operators_base.Operator):
    """
    This Operator extracts titels and other interesting text parts
    from a visual document. It does this by characterising parts
    of the text being "different" than the rest using an
    Isolation Forest algorithm (anomyla detection).
    Features are for example: font size,
    position, length etc...

    #TODO: use this for html and other kinds of text files as well...
    """

    def __call__(self, line_elements):
        line_elements = pd.DataFrame(line_elements)
        dfl = self.prepare_features(line_elements)
        return dict(
            titles=self.titles(dfl),
            side_titles=self.side_titles(dfl),
            side_content=self.side_content(dfl),
            main_content=self.normal_content(dfl)
        )

    def prepare_features(self, df_le: pd.DataFrame) -> pd.DataFrame:
        """
        detects titles and interesting textpieces from a list of text lines
        TODO: convert this function into a function of "feature-generation"
              and move the anomaly detection into the cached_property functions
        """

        # TODO: extract the necessary features that we need here "on-the-fly" from
        #       LTLineObj
        # extract more features for every line
        dfl = df_le.dropna(axis=1).copy()
        # get font with largest size to characterize line
        # TODO: this can probably be made better..  (e.g. only take the font of the "majority" content)
        dfl[['font', 'size', 'color']] = dfl.font_infos.apply(
            lambda x: pd.Series(asdict(max(x, key=operator.attrgetter("size"))))
        )

        # generate some more features
        dfl['text'] = dfl.rawtext.str.strip()
        dfl = dfl.loc[dfl.text.str.len() > 0].copy()
        dfl['length'] = dfl.text.str.len()
        dfl['wordcount'] = dfl.text.str.split().apply(len)
        dfl['vertical'] = dfl.obj.apply(lambda x: isinstance(x, LTTextLineVertical))

        dfl = dfl.join(pd.get_dummies(dfl.font, prefix="font"))
        dfl = dfl.join(pd.get_dummies(dfl.font, prefix="color"))

        features = set(dfl.columns) - {'obj', 'linewidth', 'non_stroking_color', 'stroking_color', 'stroke',
                                       'fill', 'evenodd', 'type', 'text', 'font_infos', 'font', 'rawtext',
                                       'color', 'char_orientations'}

        # detect outliers to isolate titles and other content from "normal"
        # content
        # TODO: this could be subject to some hyperparameter optimization...
        df = dfl[list(features)]
        clf = IsolationForest()  # contamination=0.05)
        clf.fit(df)
        dfl['outliers'] = clf.predict(df)

        return dfl

    def titles(self, dfl) -> typing.List:
        # titles = l.query("outliers==-1")
        titles = dfl.query("outliers==-1 and wordcount<10")
        titles = titles[titles['size'] >= titles['size'].quantile(0.75)]
        return titles.get("text", pd.Series(dtype=object)).to_list()

    def side_titles(self, dfl) -> pd.DataFrame:
        # TODO: what to do with side-titles?
        side_titles = dfl.query("outliers==-1 and wordcount<10")
        side_titles = side_titles[side_titles['size'] > dfl['size'].quantile(0.75)]
        # titles = titles[titles['size']>titles['size'].quantile(0.75)]
        return side_titles

    def side_content(self, dfl) -> str:
        # TODO: extract side-content such as addresses etc..
        side_content = "\n---\n".join(dfl[dfl.outliers == -1].text)
        return side_content

    def normal_content(self, dfl) -> str:
        # TODO: what does this function do, I forgot...
        main_content = "\n---\n".join(dfl[dfl.outliers == 1].text)
        return main_content


def get_template_elements(
        elements: pd.DataFrame,
        page_num: int = None,
        include_image: bool = False,
        vertical_elements=False
) -> pd.DataFrame:
    elements = elements.loc[elements["type"] != document_base.ElementType.Graphic].copy()
    if include_image:
        img_idxs = (elements["type"] == document_base.ElementType.Image)
        imgs = elements.loc[img_idxs]
        elements.loc[img_idxs, "rawtext"] = "{Image" + imgs.index.astype(str) + "}"
        elements = elements.loc[elements["rawtext"].str.len() > 1]
    else:
        elements = elements.loc[elements["type"] != document_base.ElementType.Image].copy()

    if page_num:
        elements = elements.loc[elements.p_num == page_num]

    if not vertical_elements:
        elements = elements.loc[elements.mean_char_orientation != 90]

    return elements


place_holder_template = "{{{}}}"


def get_area_context(
        bbox: np.ndarray,
        elements: pd.DataFrame,
        page_num: int,
        context_margin=40,
        placeholder="area"
):
    # remove all tables from elements and insert a placeholder so that
    # we can more easily query the page with LLMs

    # get text elements around the table
    el_df = get_template_elements(elements=pd.DataFrame(elements), page_num=page_num, include_image=False)

    # include boundingbox around table + context
    le = cluster_utils.boundarybox_query(
        el_df, bbox,
        tol=context_margin
    ).copy()

    # and remove elements inside area
    le = cluster_utils.boundarybox_query(
        le, bbox,
        tol=0, exclude=True
    ).copy()

    area_box = pd.DataFrame(bbox.reshape(1, -1), columns=["x0", "y0", "x1", "y1"])
    area_box["text"] = place_holder_template.format(placeholder)

    # TODO:  just use the normal "document-elements" for this instead of creating a fake
    #       area element
    boxes = pd.DataFrame(text_boxes_from_elements(le)["text_box_elements"])
    boxes = pd.concat([boxes.reset_index(), area_box], ignore_index=True).sort_values(
        by=["y0", "x0"], ascending=[False, True])

    table_context = "\n\n".join(boxes["text"].to_list())
    return table_context


class PDFDocumentObjects(pydoxtools.operators_base.Operator):
    def __init__(self):
        super().__init__()

    def __call__(
            self,
            valid_tables,
            elements: pd.DataFrame
    ) -> list[document_base.DocumentElement]:
        elements_df = get_template_elements(pd.DataFrame(elements), include_image=False)

        table_elements = []
        for table_num, table in enumerate(valid_tables):
            # table_num = 0
            # table=pdf.valid_tables[table_num]
            # page_templates={}
            # for p in pdf.page_set:
            p = table.page
            page_elements = elements_df.loc[elements_df.p_num == p]

            # page_template[p]

            # include boundingbox around table + context
            # context_margin=20
            # page_el = cluster_utils.boundarybox_query(
            #    page_elements, table.bbox,
            #    tol=context_margin
            # ).copy()

            # get indices from table
            le = cluster_utils.boundarybox_query(
                page_elements, table.bbox, tol=0
            ).copy()
            # and remove from our elements
            elements_df = elements_df.drop(le.index.tolist())
            # elements = elements[]

            # create a new "table-element"
            # table_box = pd.DataFrame(table.bbox.reshape(1,-1), columns=["x0","y0","x1","y1"])
            x0, y0, x1, y1 = table.bbox
            table_box = document_base.DocumentElement(
                type=document_base.ElementType.Table,
                x0=x0, y0=y0, x1=x1, y1=y1,
                obj=table,
                text=table.df.to_string(header=False, index=False),
                p_num=p,
                place_holder_text=f"Table{table_num}"
            )
            table_elements.append(table_box)

        # now do the textboxes
        txtboxes = text_boxes_from_elements(
            [e for e in elements if e.type == document_base.ElementType.Text]
        )["text_box_elements"]
        more_textboxes = [e for e in elements if e.type == document_base.ElementType.TextBox]
        txtboxes = pd.DataFrame(txtboxes + more_textboxes)
        # TODO: filter textboxes for vertical lines...
        # right now we're simply filtering out textboxes with just a single letter...
        txtboxes = txtboxes.loc[txtboxes.text.str.len() > 1].reset_index()
        docel_fields = {f.name for f in fields(document_base.DocumentElement)}
        # make sure we only have rows that work in our dataclass
        txtboxes = txtboxes.loc[:, txtboxes.columns.intersection(docel_fields)]

        objects = [document_base.DocumentElement(
            **{**v, "place_holder_text": f"TextBox{v.boxnum}"}
        ) for idx, v in txtboxes.T.items()]
        # txtboxes = pd.concat([txtboxes.reset_index(), table_elements],
        #                     ignore_index=True).sort_values(by=["p_num", "y0"], ascending=[True, False])

        return objects + table_elements


class PageTemplateGenerator(pydoxtools.operators_base.Operator):
    def __call__(
            self, document_objects: list[document_base.DocumentElement]
    ) -> typing.Callable[[list[str]], dict[int, str]]:
        # remove all tables from elements and insert a placeholder so that
        # we can more easily query the page with LLMs

        def generate(exclude: list[str] | document_base.ElementType = None) -> dict[int, str]:
            exclude = list_utils.ensure_list(exclude)
            objs = pd.DataFrame(document_objects)
            if objs.empty:
                return {}
            objs = objs.sort_values(by=["p_num", "y0"], ascending=[True, False])
            pages = objs.p_num.unique()
            new_text = objs.apply(
                lambda x: (place_holder_template.format(x.place_holder_text)
                           if (x.type in exclude)
                           else x.text),
                axis=1)
            page_templates = {p: "\n\n".join(new_text.dropna()[objs.p_num == p]) for p in pages}
            # page_templates = {p: "\n\n".join(objs[objs.p_num == p].text) for p in pages}

            # elements = elements.sort_values(by="y0")#.loc[(19,578)]
            return page_templates

        return generate


def get_bbox_context(
        bbox: tuple | np.ndarray, elements: list[pydoxtools.document_base.DocumentElement],
        page_num: int,
        placeholder: str = "area"
):
    """Get the context of a table from the document"""
    table_context = get_area_context(
        elements=pd.DataFrame(elements), bbox=bbox, page_num=page_num, context_margin=20,
        placeholder=placeholder
    )
    return table_context
