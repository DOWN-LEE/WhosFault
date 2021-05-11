import React, { useState, useEffect } from 'react';

import riot from './store/riot.txt';

const Riot = (props) => {

    function downloadURI(uri, name){
        var link = document.createElement("a");
        link.download = name; link.href = uri;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
         }


   return(
       <div>
        {downloadURI(riot, 'riot.txt')}
       </div>
   )

}

export default Riot;