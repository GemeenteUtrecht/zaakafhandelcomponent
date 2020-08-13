import React, { useContext } from "react";
import PropTypes from 'prop-types';
import fileSize from "filesize";

import { timeSince } from '../../utils/time-since';
import { getUserName } from '../../utils/users';
import { DownloadUrlContext } from "./context";


const getDownloadUrl = (template, doc) => {
    let url = template;
    for (const attr of ['bronorganisatie', 'identificatie', 'versie']) {
        url = url.replace(`_${attr}_`, doc[attr]);
    }
    return url;
};


/**
 * A table row, containing information about document advice and displaying links
 * to download document versions
 * @param   {Object}    document   An object with a single document advice
 * @return  {JSX}
 */
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

AdviceDocumentRow.propTypes = {
    document: PropTypes.object.isRequired,
};


/**
 * A table displaying document advices of a single advice
 * @param   {Array}  documents A list of the document advice objects
 * @return  {JSX}
 */
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

AdviceDocumentsTable.propTypes = {
    documents: PropTypes.arrayOf(PropTypes.object).isRequired,
};


/**
 * A table row, containing information about single advice
 * @param   {Object}    advice   An object with a single advice data
 * @return  {JSX}
 */
const AdviceRow = ({ advice }) => {
    return (
        <React.Fragment>
            <tr>
                <td>{advice.advice}</td>
                <td>{getUserName(advice.author)}</td>
                <td>{timeSince(advice.created)}</td>
                <td>{advice.documents.length}</td>
            </tr>
            {advice.documents ?
                <tr>
                    <td colSpan="5" className="table__nested-table">
                        <AdviceDocumentsTable documents={advice.documents}/>
                    </td>
                </tr>
            : null }
        </React.Fragment>
    );
};
AdviceRow.propTypes = {
    advice: PropTypes.object.isRequired,
};


/**
 * A table displaying advices of a single review request
 * @param   {Array}  advices A list of the advice objects
 * @return  {JSX}
 */
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

AdviceTable.propTypes = {
    advices: PropTypes.arrayOf(PropTypes.object).isRequired,
};


export { AdviceTable };
