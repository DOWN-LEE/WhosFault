import React, { useState, useEffect } from 'react';
import { Dropdown, Input, Header,Image, Container, Menu, Grid, Form, Segment, Icon  } from 'semantic-ui-react'

import './userbox.css';

const userbox=(props)=>{



    if(props.right)
        return(
        <div className='userbox_right'>
            <span>
            <img src={'http://ddragon.leagueoflegends.com/cdn/11.5.1/img/champion/'+props.champion+'.png'} className='userbox_img'/>
            </span>
            &nbsp;
            <span className='usernickname'>{props.user["summonerName"]}</span>
        </div>
        )
    else
        return(
        <div className='userbox_left'>
            <span className='usernickname'>{props.user["summonerName"]}</span>
            &nbsp;
            <span>
            <img src={'http://ddragon.leagueoflegends.com/cdn/11.5.1/img/champion/'+props.champion+'.png'} className='userbox_img'/>
            </span>
            
        </div>
        )
}

export default userbox