import React from 'react';
import PropTypes from 'prop-types';

import { VERTROUWELIJKHEIDAANDUIDINGEN } from '../../constants';

const VA_DISPLAY = Object.fromEntries(new Map(VERTROUWELIJKHEIDAANDUIDINGEN));

const PermissionsToDelete = ({ catalogus, existingFormData }) => {
    const toDelete = existingFormData.filter(fd => fd.catalogus !== catalogus);
    if (!toDelete.length) {
        return null;
    }
    return (
        <>
            {/* TODO: fix classname */}
            <div className="permission-check permission-check--failed" style={{marginTop: '1em'}}>
                De volgende documenttype-permissies worden verwijderd
            </div>

            <ul className="list" style={{marginBottom: '1em'}}>
            { toDelete.map((fd, index) => (
                <li className="list__item" key={fd.id} style={{marginTop: '5px', paddingLeft: '1em'}}>
                    <strong>{fd.omschrijving}</strong> {`(${VA_DISPLAY[fd.max_va]})`}
                </li>
            )) }
            </ul>
        </>
    );
};

PermissionsToDelete.propTypes = {
    catalogus: PropTypes.string.isRequired,
    existingFormData: PropTypes.arrayOf(PropTypes.shape({
        catalogus: PropTypes.string.isRequired,
        omschrijving: PropTypes.string.isRequired,
        max_va: PropTypes.string.isRequired,
    }))
};


export default PermissionsToDelete;
