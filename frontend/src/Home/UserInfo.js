import React, { useState, useEffect } from 'react';
import { Dropdown, Input, Header,Image, Container, Menu, Grid, Form, Segment, Loader  } from 'semantic-ui-react'
import RankBox from './RankBox';

import './UserInfo.css';


const UserInfo = (props) => {

    return(
        <div>
            <Grid>
                <Grid.Row only='tablet mobile' verticalAlign='middle'>
                    <span>
                    <img src={'http://ddragon.leagueoflegends.com/cdn/11.3.1/img/profileicon/'+props.userProfile+'.png'} className='profile_img_mobile'/>
                    </span>
                    <span>
                    <div className='profile_name_mobile'>
                        {props.userName}
                    </div>
                    <div className='profile_level_mobile'>
                        LV. {props.userLevel}
                    </div>
                    </span>
                    
                </Grid.Row>
            </Grid>


            <Segment  className='profile_box'>
            <Grid>
                
                <Grid.Row  only='computer' columns={2}>
                    <Grid.Column textAlign='left'>
                        <span>
                            <span>
                            <img src={'http://ddragon.leagueoflegends.com/cdn/11.3.1/img/profileicon/'+props.userProfile+'.png'} className='profile_img'/>
                            </span> 
                            <span className='profile_name'>
                            <div className='profile_name1'>
                                {props.userName}
                            </div>
                            <div className='profile_level'>
                                LV. {props.userLevel}
                            </div>
                            </span>
                        </span>
                    </Grid.Column>
                    <Grid.Column textAlign='right'  >
                
                        <RankBox rankinfo={props.userFlexRank} isSolo={false}/>  
                        
                        <RankBox rankinfo={props.userSoloRank} isSolo={true}/>
                                
                        
                    </Grid.Column>
                </Grid.Row>

                <Grid.Row only='tablet mobile' centered ci   >
                    
                
                        <RankBox rankinfo={props.userSoloRank} mobile={true} className='mobile_box1' isSolo={true}/>
                        <RankBox rankinfo={props.userFlexRank} mobile={true} className='mobile_box2' isSolo={false}/>
                    

                </Grid.Row>
            
            </Grid>

            </Segment>
        </div>
    )
}


export default UserInfo;