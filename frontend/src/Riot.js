import React, { useState, useEffect } from 'react';

import riot from './store/riot.txt';

const Riot = (props) => {

    function downloadURI(){
        fetch('./store/riot.txt').then((r) => r.json());
    }


   return(
       <div>
        {downloadURI()}
       </div>
   )

}

export default Riot;