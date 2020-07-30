import React, { useContext } from "react";
import fileSize from "filesize";
import moment from "moment";
import 'moment/locale/nl.js';

import {getAuthorName} from "./utils";
import {DownloadUrlContext} from "./context";

moment.locale('nl');


const getDownloadUrl = (template, doc) => {
    let url = template;
    for (const attr of ['bronorganisatie', 'identificatie', 'versie']) {
        url = url.replace(`_${attr}_`, doc[attr]);
    }
    return url;
};


const AdviceDocumentRow = ({document}) => {
    const source = document.source;
    const advice = document.advice;
    const downloadUrlTemlate = useContext(DownloadUrlContext);

    return (
        <tr>
            <td>
                <strong>{source.titel}</strong>:&nbsp;
                <span className="table__id-column">
                    <a
                        href={getDownloadUrl(downloadUrlTemlate, source)}
                        target="_blank" rel="nofollow noopener">
                        { source.bestandsnaam ? source.bestandsnaam : source.identificatie }
                    </a>
                </span>
                {`(versie ${source.versie} — ${fileSize(source.bestandsomvang)})`}
            </td>
            <td>
            <span className="table__id-column">
                <a
                    href={getDownloadUrl(downloadUrlTemlate, advice)}
                    target="_blank" rel="nofollow noopener">
                    { advice.bestandsnaam ? advice.bestandsnaam : advice.identificatie }
                </a>
            </span>
                {`(versie ${advice.versie} — ${fileSize(advice.bestandsomvang)})`}
            </td>
        </tr>
    )
};


const AdviceDocumentsTable = ({ documents }) => {
    const rows = documents.map((document, index) =>
        <AdviceDocumentRow key={index} document={document}/>
    );

    return (
        <table className="table">
            <thead>
            <tr>
                <td className="table__subheader">Brondocument</td>
                <td className="table__subheader">Aantekeningen/bijgewerkte versie</td>
            </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    );
};


const AdviceRow = ({ advice }) => {
    return (
        <>
            <tr>
                <td>{advice.advice}</td>
                <td>{getAuthorName(advice.author)}</td>
                <td>{moment(advice.created).fromNow()}</td>
                <td>{advice.documents.length}</td>
            </tr>
            {advice.documents ?
                <tr>
                    <td colSpan="5" className="table__nested-table">
                        <AdviceDocumentsTable documents={advice.documents}/>
                    </td>
                </tr>
            : null }
        </>
    );
};


const AdviceTable = ({ advices }) => {
    const rows = advices.map((advice, index) =>
        <AdviceRow key={index} advice={advice}/>
    );

    return (
        <section className="zaak-detail__panel zaak-detail__panel--full content-panel">
            <div className="section-title">Adviezen</div>
            {!(advices.length) ?
                <p className="content-panel__content content-panel__content--blurred">
                    (geen adviezen)
                </p>
                : <table className="table">
                    <thead>
                    <tr>
                        <th className="table__header">Advies</th>
                        <th className="table__header">Van</th>
                        <th className="table__header">Gegeven op</th>
                        <th className="table__header">Documentadviezen</th>
                    </tr>
                    </thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
            }
        </section>
    );
};


export { AdviceTable };
